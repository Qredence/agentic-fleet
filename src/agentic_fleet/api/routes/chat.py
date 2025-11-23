"""Chat API routes."""

import json
from collections.abc import AsyncGenerator

from agent_framework import MagenticAgentMessageEvent, WorkflowOutputEvent, WorkflowStatusEvent
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
from agentic_fleet.workflows.supervisor import create_supervisor_workflow

router = APIRouter()

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
    # TODO: Pass conversation history if supported by SupervisorWorkflow in the future
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
                # Only yield messages from actual agents, skip user/system messages
                if event.agent_id not in ["orchestrator", "critic_verifier", "synthesis_generator"]:
                    continue

                content = event.message.text
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

            elif isinstance(event, WorkflowOutputEvent):
                # Final result
                # If we haven't streamed any content yet (e.g. Fast Path), send the result now
                if not full_response and event.data and isinstance(event.data, dict):
                    result = event.data.get("result")
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
        error_msg = {"type": "error", "error": str(e)}
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
