"""Chat API routes."""

import json
from collections.abc import AsyncGenerator

from agent_framework._workflows import (
    ExecutorCompletedEvent,
    MagenticAgentMessageEvent,
    WorkflowOutputEvent,
    WorkflowStatusEvent,
)
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from agentic_fleet.api.db.session import get_db_session
from agentic_fleet.api.dependencies import Logger
from agentic_fleet.api.schemas.chat import (
    ChatRequest,
    ChatResponse,
    Conversation,
    ConversationListResponse,
    CreateConversationRequest,
    Message,
)
from agentic_fleet.api.services import conversation_service
from agentic_fleet.utils.config_loader import load_config
from agentic_fleet.workflows.messages import (
    AnalysisMessage,
    ExecutionMessage,
    ProgressMessage,
    QualityMessage,
    RoutingMessage,
)
from agentic_fleet.workflows.supervisor import create_supervisor_workflow

router = APIRouter()

# Load API configuration
_config = load_config()
_api_config = _config.get("api", {})
_chat_config = _api_config.get("chat", {})
# Agent IDs to include in streaming responses (only these will be shown)
INCLUDED_AGENT_IDS = _chat_config.get(
    "included_agent_ids", ["orchestrator", "critic_verifier", "synthesis_generator"]
)

# --- Routes ---


@router.post("/conversations", response_model=Conversation)
async def create_conversation(
    request: CreateConversationRequest | None = None,
    db: AsyncSession = Depends(get_db_session),
):
    """Create a new conversation."""
    if request is None:
        request = CreateConversationRequest()
    return await conversation_service.create_conversation(db, title=request.title)


@router.get("/conversations", response_model=ConversationListResponse)
async def list_conversations(
    db: AsyncSession = Depends(get_db_session),
):
    """List all conversations."""
    convs = await conversation_service.list_conversations(db)
    conv_models = [Conversation.model_validate(conv) for conv in convs]
    return ConversationListResponse(items=conv_models)


@router.get("/conversations/{conversation_id}", response_model=Conversation)
async def get_conversation(
    conversation_id: str,
    db: AsyncSession = Depends(get_db_session),
):
    """Get a specific conversation."""
    try:
        conv_id_int = int(conversation_id)
    except ValueError as err:
        raise HTTPException(status_code=404, detail="Conversation not found") from err

    conv = await conversation_service.get_conversation(db, conv_id_int)
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return conv


@router.post("/chat")
async def chat(
    request: ChatRequest,
    logger: Logger,
    db: AsyncSession = Depends(get_db_session),
):
    """Send a message to the agent."""
    try:
        conv_id_int = int(request.conversation_id)
    except ValueError as err:
        raise HTTPException(status_code=404, detail="Conversation not found") from err

    conv = await conversation_service.get_conversation(db, conv_id_int)
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation not found")

    # Save user message
    user_msg = Message(id=None, content=request.message, role="user")
    await conversation_service.add_message_to_conversation(db, conv_id_int, user_msg)

    if request.stream:
        return StreamingResponse(
            stream_chat_generator(conv_id_int, request.message, db, logger),
            media_type="text/event-stream",
        )
    else:
        # Non-streaming fallback (simplified, ideally reuse workflow logic)
        # For now, we enforce streaming in frontend, but let's implement basic blocking call
        workflow = await create_supervisor_workflow()
        result = await workflow.run(request.message)

        response_text = result.get("result", "")
        # Save assistant message
        asst_msg = Message(id=None, content=response_text, role="assistant")
        await conversation_service.add_message_to_conversation(db, conv_id_int, asst_msg)

        # Reload conversation to get updated messages
        conv = await conversation_service.get_conversation(db, conv_id_int)
        if conv is None:
            raise HTTPException(status_code=404, detail="Conversation not found")

        conv_model = Conversation.model_validate(conv)
        return ChatResponse(
            conversation_id=conv_model.id or conv_id_int,
            message=response_text,
            messages=conv_model.messages,
        )


async def stream_chat_generator(
    conversation_id: int, message: str, db: AsyncSession, logger: Logger
) -> AsyncGenerator[str, None]:
    """Stream chat response from SupervisorWorkflow."""

    # Initialize workflow
    # NOTE: Conversation history integration planned for future release.
    # Currently, each workflow run is stateless. To support multi-turn conversations:
    # 1. Load history via PersistenceManager.get_conversation_history(conversation_id)
    # 2. Pass history to create_supervisor_workflow() or include in context
    # 3. Update SupervisorContext to maintain message history across runs
    workflow = await create_supervisor_workflow()

    # 1. Send orchestrator thought (start)
    orchestrator_msg = {
        "type": "orchestrator.message",
        "message": "Starting workflow...",
        "kind": "thought",
    }
    yield f"data: {json.dumps(orchestrator_msg)}\n\n"

    full_response = ""

    try:
        async for event in workflow.run_stream(message):
            if isinstance(event, MagenticAgentMessageEvent):
                # Only yield messages from specific orchestration agents
                if event.agent_id not in INCLUDED_AGENT_IDS:
                    continue

                content = event.message.text if event.message else None
                if content:
                    full_response += content
                    delta_msg = {
                        "type": "response.delta",
                        "delta": content,
                        "agent_id": event.agent_id,
                    }
                    yield f"data: {json.dumps(delta_msg)}\n\n"

            elif isinstance(event, WorkflowStatusEvent):
                # Status update
                status_msg = {
                    "type": "orchestrator.message",
                    "message": f"Status: {event.state}",
                    "kind": "status",
                }
                yield f"data: {json.dumps(status_msg)}\n\n"

            elif isinstance(event, ExecutorCompletedEvent):
                output = getattr(event, "output", None)
                thought_data = None

                if isinstance(output, AnalysisMessage):
                    thought_data = {
                        "title": "Analysis",
                        "description": f"Complexity: {output.analysis.complexity}, Steps: {output.analysis.steps}",
                        "status": "success",
                        "items": [
                            {"type": "text", "text": f"Complexity: {output.analysis.complexity}"},
                            {
                                "type": "text",
                                "text": f"Capabilities: {', '.join(output.analysis.capabilities)}",
                            },
                            {"type": "text", "text": f"Steps: {output.analysis.steps}"},
                        ],
                    }
                elif isinstance(output, RoutingMessage):
                    thought_data = {
                        "title": "Routing",
                        "description": f"Mode: {output.routing.decision.mode.value}, Agents: {len(output.routing.decision.assigned_to)}",
                        "status": "success",
                        "items": [
                            {"type": "text", "text": f"Mode: {output.routing.decision.mode.value}"},
                            {
                                "type": "text",
                                "text": f"Assigned: {', '.join(output.routing.decision.assigned_to)}",
                            },
                        ],
                    }
                elif isinstance(output, ExecutionMessage):
                    thought_data = {
                        "title": "Execution",
                        "description": "Task execution completed",
                        "status": output.outcome.status,
                        "items": [
                            {"type": "text", "text": f"Status: {output.outcome.status}"},
                        ],
                    }
                elif isinstance(output, ProgressMessage):
                    thought_data = {
                        "title": "Progress Evaluation",
                        "description": f"Action: {output.progress.action}",
                        "status": "success",
                        "items": [
                            {"type": "text", "text": f"Action: {output.progress.action}"},
                            {"type": "text", "text": f"Feedback: {output.progress.feedback}"},
                        ],
                    }
                elif isinstance(output, QualityMessage):
                    thought_data = {
                        "title": "Quality Assessment",
                        "description": f"Score: {output.quality.score}",
                        "status": "success",
                        "items": [
                            {"type": "text", "text": f"Score: {output.quality.score}"},
                            {"type": "text", "text": f"Missing: {output.quality.missing}"},
                        ],
                    }

                if thought_data:
                    yield f"data: {json.dumps({'type': 'orchestrator.thought', 'thought': thought_data})}\n\n"

            elif isinstance(event, WorkflowOutputEvent):
                # Final result
                # If we haven't streamed any content yet (e.g. Fast Path), send the result now
                if not full_response and event.data:
                    result = None
                    if isinstance(event.data, dict):
                        result = event.data.get("result")
                    elif isinstance(event.data, list) and len(event.data) > 0:
                        # New format: list[ChatMessage]
                        last_msg = event.data[-1]
                        additional_props = getattr(last_msg, "additional_properties", {}) or {}
                        result = getattr(last_msg, "text", None) or additional_props.get("result")
                    if result:
                        full_response = result
                        delta_msg = {
                            "type": "response.delta",
                            "delta": result,
                            "agent_id": event.source_executor_id,
                        }
                        yield f"data: {json.dumps(delta_msg)}\n\n"

    except Exception as e:
        logger.error(f"Error in stream_chat_generator: {e}", exc_info=True)
        error_msg = {"type": "error", "error": "An internal error occurred."}
        yield f"data: {json.dumps(error_msg)}\n\n"
        # Still send completion events to properly terminate the stream
        done_msg = {"type": "response.completed"}
        yield f"data: {json.dumps(done_msg)}\n\n"
        yield "data: [DONE]\n\n"
        return

    # Save assistant message to DB
    if full_response:
        asst_msg = Message(id=None, content=full_response, role="assistant")
        await conversation_service.add_message_to_conversation(db, conversation_id, asst_msg)

    # 4. Send completion event
    done_msg = {"type": "response.completed"}
    yield f"data: {json.dumps(done_msg)}\n\n"

    # 5. End stream
    yield "data: [DONE]\n\n"
