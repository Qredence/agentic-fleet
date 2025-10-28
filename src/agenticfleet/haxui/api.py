
import json
from typing import Any, AsyncIterator
from uuid import uuid4
from fastapi import FastAPI, Depends, HTTPException, Request, Response, status
from fastapi.responses import StreamingResponse

 -> Response:
        await store.delete(conversation_id)
        return Response(status_code=status.HTTP_204_NO_CONTENT)

    @app.get(
        "/v1/conversations/{conversation_id}/items",
        response_model=ConversationItemsResponse,
    )
    async def list_conversation_items(
        conversation_id: str,
        store: ConversationStore = Depends(get_conversation_store),
    ) -> ConversationItemsResponse:
        try:
            return await store.list_items(conversation_id)
        except KeyError as e:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Conversation not found."
            ) from e

    @app.get("/v1/approvals", response_model=ApprovalListResponse)
    async def list_approvals(
        handler: WebApprovalHandler = Depends(get_approval_handler),
    ) -> ApprovalListResponse:
        pending = await handler.get_pending_requests()
        items = [
            ApprovalRequestInfo(
                request_id=item["request_id"],
                operation_type=item["operation_type"],
                agent_name=item["agent_name"],
                operation=item["operation"],
                details=item.get("details") or {},
                code=item.get("code"),
                status=item.get("status", "pending"),
                timestamp=item["timestamp"],
            )
            for item in pending
        ]
        return ApprovalListResponse(data=items)

    @app.post(
        "/v1/approvals/{request_id}",
        status_code=status.HTTP_204_NO_CONTENT,
    )
    async def respond_to_approval(
        request_id: str,
        payload: ApprovalDecisionRequest,
        runtime: FleetRuntime = Depends(get_runtime),
    ) -> Response:
        try:
            decision = ApprovalDecision(payload.decision.lower())
        except ValueError as exc:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Unsupported decision '{payload.decision}'",
            ) from exc

        if decision == ApprovalDecision.MODIFIED and not payload.modified_code:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="modified_code is required when decision is 'modified'.",
            )

        handled = await runtime.approval_handler.set_approval_response(
            request_id,
            decision,
            modified_code=payload.modified_code,
            reason=payload.reason,
        )
        if not handled:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Approval request not found or already handled.",
            )
        return Response(status_code=status.HTTP_204_NO_CONTENT)

    @app.post("/v1/workflow/dynamic")
    async def run_dynamic_orchestration_workflow(
        request: Request,
        store: ConversationStore = Depends(get_conversation_store),
    ) -> StreamingResponse:
        """
        Dedicated endpoint for dynamic orchestration workflow.

        This endpoint creates a dynamic Magentic workflow with on-demand
        agent spawning.

        Request Body:
            {
                "query": "Your task here",
                "manager_model": "gpt-4o",       // optional
                "conversation_id": "conv_123"    // optional
            }

        Returns:
            Server-Sent Events stream with agent responses and tool outputs
        """
        try:
            from agenticfleet.workflows.dynamic_orchestration.factory import (
                create_dynamic_group_chat_workflow,
            )
        except ImportError as exc:
            raise HTTPException(
                status_code=status.HTTP_501_NOT_IMPLEMENTED,
                detail="Dynamic orchestration module not available",
            ) from exc

        payload = await request.json()
        query = payload.get("query")
        if not query or not isinstance(query, str):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Missing or invalid 'query' field.",
            )

        manager_model = payload.get("manager_model", "gpt-4o")
        conversation_id = payload.get("conversation_id")

        # Create or validate conversation
        if conversation_id:
            try:
                await store.get(conversation_id)
            except KeyError:
                conversation_id = None

        if conversation_id is None:
            summary = await store.create(
                metadata={"workflow": "dynamic_orchestration", "auto_created": "true"}
            )
            conversation_id = summary.id

        # Add user message to conversation
        user_content = [{"type": "text", "text": query}]
        await store.add_message(conversation_id, "user", user_content)

        # Create dynamic workflow with query for complexity detection
        workflow, _ = create_dynamic_group_chat_workflow(
            manager_model=manager_model,
            tool_registry=None,
            query=query,  # Pass query for adaptive max_rounds
        )

        async def stream_dynamic_workflow() -> AsyncIterator[bytes]:
            """Stream events from the dynamic orchestration workflow."""
            message_id = f"msg_{uuid4().hex[:12]}"
            sequence_number = 0
            accumulated = ""

            try:
                async for event in workflow.run_stream(query):
                    payloads, _ = translate_dynamic_event(event, message_id=message_id)
                    for payload in payloads:
                        sequence_number += 1
                        payload["sequence_number"] = sequence_number
                        if payload["type"] == "response.output_text.delta":
                            payload.setdefault("actor", "assistant")
                            payload.setdefault("role", "assistant")
                            accumulated += payload.get("delta", "")
                        elif payload["type"] == "workflow.event":
                            payload.setdefault("actor", "workflow")
                            payload.setdefault("role", "system")
                            payload.setdefault("message_id", message_id)
                        yield SSEEventEmitter.emit_raw(payload)

                if accumulated:
                    assistant_content = [{"type": "text", "text": accumulated}]
                    await store.add_message(conversation_id, "assistant", assistant_content)

                response_payload = build_response_payload(
                    conversation_id=conversation_id,
                    entity_id=manager_model,
                    assistant_text=accumulated,
                    usage={"input_tokens": None, "output_tokens": None, "total_tokens": None},
                    queue_metrics=None,
                )
                yield SSEEventEmitter.emit_response_completed(
                    response=response_payload["response"],
                    sequence_number=sequence_number + 1,
                    queue_metrics=response_payload.get("queue_metrics"),
                )

            except Exception as exc:
                LOGGER.error(f"Dynamic workflow streaming error: {exc}", exc_info=True)
                yield SSEEventEmitter.emit_raw(
                    {
                        "type": "error",
                        "error": {"message": str(exc), "type": "workflow_error"},
                    }
                )
            finally:
                yield SSEEventEmitter.emit_done()

        return StreamingResponse(
            stream_dynamic_workflow(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no",
            },
        )

    @app.post("/v1/workflow/optimized")
    async def run_optimized_workflow(
        request: Request,
        store: ConversationStore = Depends(get_conversation_store),
    ) -> StreamingResponse:
        """
        Optimized workflow endpoint with intelligent routing.

        Uses executor pattern for:
        - Fast path for trivial/simple queries (<1-2s)
        - Adaptive complexity-based routing
        - Full event visibility with reasoning
        - Agent spawning only when needed

        Request Body:
            {
                "query": "Your task here",
                "manager_model": "gpt-4o",       // optional
                "conversation_id": "conv_123"    // optional
            }

        Returns:
            Server-Sent Events stream with detailed reasoning and events
        """
        try:
            from agenticfleet.workflows.dynamic_orchestration.factory import (
                create_optimized_workflow_response,
            )
        except ImportError as exc:
            raise HTTPException(
                status_code=status.HTTP_501_NOT_IMPLEMENTED,
                detail="Optimized workflow module not available",
            ) from exc

        payload = await request.json()
        query = payload.get("query")
        if not query or not isinstance(query, str):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Missing or invalid 'query' field.",
            )

        manager_model = payload.get("manager_model", "gpt-4o")
        conversation_id = payload.get("conversation_id")

        # Create or validate conversation
        if conversation_id:
            try:
                await store.get(conversation_id)
            except KeyError:
                conversation_id = None

        if conversation_id is None:
            summary = await store.create(metadata={"workflow": "optimized", "auto_created": "true"})
            conversation_id = summary.id

        # Add user message to conversation
        user_content = [{"type": "text", "text": query}]
        await store.add_message(conversation_id, "user", user_content)

        async def stream_optimized_workflow() -> AsyncIterator[bytes]:
            """Stream events from optimized workflow with full reasoning."""
            message_id = f"msg_{uuid4().hex[:12]}"
            sequence_number = 0

            try:
                # Get workflow result with events
                result = await create_optimized_workflow_response(
                    query=query,
                    manager_model=manager_model,
                )

                # Stream all events with reasoning
                for event in result["events"]:
                    sequence_number += 1

                    # Format event for frontend
                    event_payload = {
                        "type": event.get("type", "workflow.event"),
                        "message_id": message_id,
                        "sequence_number": sequence_number,
                        "actor": event.get("actor", "System"),
                        "role": event.get("role", "system"),
                        "reasoning": event.get("reasoning", ""),
                        "confidence": event.get("confidence"),
                        "complexity": event.get("complexity"),
                        "data": event,
                    }

                    yield SSEEventEmitter.emit_raw(event_payload)

                # If fast path, emit response
                if result.get("fast_path") and result.get("response"):
                    # Emit final response
                    response_text = result["response"]

                    # Stream response as deltas
                    for char in response_text:
                        sequence_number += 1
                        yield SSEEventEmitter.emit_raw(
                            {
                                "type": "response.output_text.delta",
                                "message_id": message_id,
                                "sequence_number": sequence_number,
                                "delta": char,
                                "actor": "Direct Response",
                                "role": "assistant",
                            }
                        )

                    # Store in conversation
                    assistant_content = [{"type": "text", "text": response_text}]
                    await store.add_message(conversation_id, "assistant", assistant_content)

                    # Emit completion
                    sequence_number += 1
                    response_payload = build_response_payload(
                        conversation_id=conversation_id,
                        entity_id=manager_model,
                        assistant_text=response_text,
                        usage={"input_tokens": None, "output_tokens": None, "total_tokens": None},
                        queue_metrics=None,
                    )
                    yield SSEEventEmitter.emit_response_completed(
                        response=response_payload["response"],
                        sequence_number=sequence_number,
                    )
                else:
                    # Complex path - would continue with workflow
                    # For now, emit info message
                    sequence_number += 1
                    yield SSEEventEmitter.emit_raw(
                        {
                            "type": "workflow.event",
                            "message_id": message_id,
                            "sequence_number": sequence_number,
                            "actor": "System",
                            "role": "system",
                            "reasoning": "Complex query requires full workflow execution",
                            "event_type": "progress",
                            "text": "Continuing with full workflow...",
                        }
                    )

            except Exception as e:
                LOGGER.exception("Error in optimized workflow")
                sequence_number += 1
                yield SSEEventEmitter.emit_raw(
                    {
                        "type": "workflow.error",
                        "message_id": message_id,
                        "sequence_number": sequence_number,
                        "error": str(e),
                        "actor": "System",
                        "role": "system",
                        "reasoning": f"Workflow execution failed: {e!r}",
                    }
                )

        return StreamingResponse(
            stream_optimized_workflow(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no",
            },
        )

    @app.post("/v1/workflow/reflection")
    async def run_reflection_workflow(
        request: Request,
        store: ConversationStore = Depends(get_conversation_store),
    ) -> StreamingResponse:
        """
        Dedicated endpoint for workflow_as_agent (Reflection & Retry pattern).

        This endpoint creates a Worker-Reviewer workflow that iteratively
        improves responses through quality feedback loops.

        Request Body:
            {
                "query": "Your question here",
                "worker_model": "gpt-4.1-nano",  // optional
                "reviewer_model": "gpt-4.1",     // optional
                "conversation_id": "conv_123"    // optional
            }

        Returns:
            Server-Sent Events stream with Worker responses and Reviewer feedback
        """
        payload = await request.json()
        query = payload.get("query")
        if not query or not isinstance(query, str):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Missing or invalid 'query' field.",
            )

        worker_model = payload.get("worker_model", "gpt-4.1-nano")
        reviewer_model = payload.get("reviewer_model", "gpt-4.1")
        conversation_id = payload.get("conversation_id")

        # Create or validate conversation
        if conversation_id:
            try:
                await store.get(conversation_id)
            except KeyError:
                conversation_id = None

        if conversation_id is None:
            summary = await store.create(
                metadata={"workflow": "reflection", "auto_created": "true"}
            )
            conversation_id = summary.id

        # Add user message to conversation
        user_content = [{"type": "text", "text": query}]
        await store.add_message(conversation_id, "user", user_content)

        # Create workflow agent
        agent = create_workflow_agent(worker_model=worker_model, reviewer_model=reviewer_model)

        async def stream_workflow() -> AsyncIterator[bytes]:
            """Stream events from the workflow agent."""
            message_id = f"msg_{uuid4().hex[:12]}"
            sequence_number = 0
            accumulated = ""

            try:
                # Stream events from workflow
                async for event in agent.run_stream(query):
                    sequence_number += 1

                    if isinstance(event, AgentRunUpdateEvent):
                        actual_event = getattr(event, "data", event)
                    else:
                        actual_event = event

                    text = getattr(actual_event, "text", None)
                    author_name: str | None = getattr(actual_event, "author_name", None)
                    role_value = None

                    if isinstance(actual_event, AgentRunResponseUpdate):
                        role_value = _extract_role_value(getattr(actual_event, "role", None))
                    else:
                        text = str(actual_event)

                    raw_text = text if text is not None else str(actual_event)

                    if role_value == ASSISTANT_ROLE_VALUE:
                        accumulated += raw_text
                        yield SSEEventEmitter.emit_raw(
                            {
                                "type": "response.output_text.delta",
                                "delta": raw_text,
                                "item_id": message_id,
                                "output_index": 0,
                                "sequence_number": sequence_number,
                                "actor": author_name or "assistant",
                                "role": "assistant",
                            }
                        )
                    else:
                        log_text = raw_text.strip()
                        if not log_text:
                            continue
                        yield SSEEventEmitter.emit_raw(
                            {
                                "type": "workflow.event",
                                "actor": author_name or "workflow",
                                "text": log_text,
                                "role": role_value or "system",
                                "message_id": message_id,
                                "sequence_number": sequence_number,
                            }
                        )

                # Save assistant response to conversation
                assistant_content = [{"type": "text", "text": accumulated}]
                await store.add_message(conversation_id, "assistant", assistant_content)

                # Send completion
                sequence_number += 1
                # Calculate token usage
                input_tokens: int | None = None
                output_tokens: int | None = None
                total_tokens: int | None = None

                if tiktoken is not None:
                    try:
                        encoding = tiktoken.encoding_for_model(worker_model)
                        input_tokens = len(encoding.encode(query))
                        output_tokens = len(encoding.encode(accumulated))
                        total_tokens = input_tokens + output_tokens
                    except (KeyError, Exception):
                        pass  # Already initialized to None above

                yield SSEEventEmitter.emit_raw(
                    {
                        "type": "response.done",
                        "conversation_id": conversation_id,
                        "message_id": message_id,
                        "sequence_number": sequence_number,
                        "usage": {
                            "input_tokens": input_tokens,
                            "output_tokens": output_tokens,
                            "total_tokens": total_tokens,
                        },
                    }
                )
                yield b"data: [DONE]\n\n"
                yield b"data: [DONE]\n\n"

            except Exception as exc:
                # Log full error internally
                import logging

                logger = logging.getLogger(__name__)
                logger.error(f"Workflow error: {exc}", exc_info=True)

                # Send generic error to client using SSEEventEmitter
                sequence_number += 1
                error_sse = SSEEventEmitter.emit_error(
                    error="Workflow Execution Error",
                    details="An error occurred during workflow execution",
                    recoverable=False,
                )
                yield error_sse
                yield b"data: [DONE]\n\n"

        return StreamingResponse(stream_workflow(), media_type="text/event-stream")

    @app.post("/v1/responses")
    async def create_response(
        request: Request,
        runtime: FleetRuntime = Depends(get_runtime),
        store: ConversationStore = Depends(get_conversation_store),
    ) -> StreamingResponse:
        payload = await request.json()
        model = payload.get("model")
        if not isinstance(model, str):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail="Missing model field."
            )

        input_payload = extract_input_payload(payload)
        user_text = extract_user_text(payload.get("input"))
        approval_response = extract_approval_response(payload.get("input"))

        conversation_ref = payload.get("conversation")
        conversation_id = None
        if isinstance(conversation_ref, dict):
            conversation_id = conversation_ref.get("id")
        elif isinstance(conversation_ref, str):
            conversation_id = conversation_ref

        if conversation_id:
            try:
                await store.get(conversation_id)
            except KeyError:
                conversation_id = None

        if conversation_id is None:
            summary = await store.create(metadata={"auto_created": "true"})
            conversation_id = summary.id

        # Handle approval response if present
        if approval_response:
            request_id = approval_response.get("request_id")
            if request_id is None:
                raise ValueError("Approval response missing request_id")
            approved = approval_response.get("approved", False)
            decision = ApprovalDecision.APPROVED if approved else ApprovalDecision.REJECTED

            # Set approval response on the runtime's handler
            await runtime.approval_handler.set_approval_response(request_id, decision)

            # Don't add user message for approval responses - they're control messages
            # Just return success event
            async def approval_ack_stream() -> AsyncIterator[bytes]:
                yield SSEEventEmitter.emit_approval_responded(
                    request_id=request_id,
                    approved=approved,
                    sequence_number=1,
                )
                yield SSEEventEmitter.emit_done()

            return StreamingResponse(approval_ack_stream(), media_type="text/event-stream")

        # Regular message - add to conversation
        user_content_blocks: list[dict[str, Any]] = []
        if user_text:
            user_content_blocks.append({"type": "text", "text": user_text})
        elif input_payload:
            user_content_blocks.append({"type": "text", "text": json.dumps(input_payload)})

        if user_content_blocks:
            try:
                await store.add_message(conversation_id, "user", user_content_blocks)
            except KeyError:
                # Conversation was deleted between creation and now - recreate.
                summary = await store.create(metadata={"auto_recreated": "true"})
                conversation_id = summary.id
                await store.add_message(conversation_id, "user", user_content_blocks)

        # INTELLIGENT ROUTING: Check if query is simple and route to optimized workflow
        if (
            OPTIMIZED_WORKFLOW_AVAILABLE
            and user_text
            and is_simple_query(user_text)
            and model == "dynamic_orchestration"
        ):
            LOGGER.info(f"Routing simple query to optimized workflow: {user_text!r}")

            async def stream_optimized() -> AsyncIterator[bytes]:
                """Stream optimized workflow events with reasoning."""
                message_id = f"msg_{uuid4().hex[:12]}"
                sequence_number = 0

                try:
                    # Get optimized workflow result
                    if create_optimized_workflow_response is None:
                        raise RuntimeError("Optimized workflow factory is unavailable")
                    result = await create_optimized_workflow_response(
                        query=user_text,
                        manager_model="gpt-4o",
                    )

                    # Stream all events with reasoning/confidence/complexity
                    for event in result["events"]:
                        sequence_number += 1

                        # Emit workflow event with full context
                        yield SSEEventEmitter.emit_raw(
                            {
                                "type": "workflow.event",
                                "message_id": message_id,
                                "sequence_number": sequence_number,
                                "actor": event.get("actor", "System"),
                                "role": event.get("role", "system"),
                                "reasoning": event.get("reasoning", ""),
                                "confidence": event.get("confidence"),
                                "complexity": event.get("complexity"),
                                "text": event.get("response", ""),
                                "event_type": event.get("type", "info"),
                            }
                        )

                    # If fast path, emit response as delta stream
                    if result.get("fast_path") and result.get("response"):
                        response_text = result["response"]

                        # Stream character by character for smooth UX
                        for char in response_text:
                            sequence_number += 1
                            yield SSEEventEmitter.emit_raw(
                                {
                                    "type": "response.output_text.delta",
                                    "message_id": message_id,
                                    "item_id": message_id,
                                    "sequence_number": sequence_number,
                                    "delta": char,
                                    "actor": "Direct Response",
                                    "role": "assistant",
                                }
                            )

                        # Store assistant response
                        assistant_content = [{"type": "text", "text": response_text}]
                        await store.add_message(conversation_id, "assistant", assistant_content)

                        # Emit completion event
                        sequence_number += 1
                        response_payload = build_response_payload(
                            conversation_id=conversation_id,
                            entity_id=model,
                            assistant_text=response_text,
                            usage={
                                "input_tokens": None,
                                "output_tokens": None,
                                "total_tokens": None,
                            },
                            queue_metrics=None,
                        )
                        yield SSEEventEmitter.emit_response_completed(
                            response=response_payload["response"],
                            sequence_number=sequence_number,
                        )

                    yield SSEEventEmitter.emit_done()

                except Exception as exc:
                    LOGGER.exception("Error in optimized workflow")
                    sequence_number += 1
                    yield SSEEventEmitter.emit_raw(
                        {
                            "type": "error",
                            "message_id": message_id,
                            "sequence_number": sequence_number,
                            "error": str(exc),
                            "message": f"Optimized workflow failed: {exc!r}",
                        }
                    )
                    yield SSEEventEmitter.emit_done()

            return StreamingResponse(stream_optimized(), media_type="text/event-stream")

        # STANDARD PATH: Use existing runtime for complex queries
        streaming_config = StreamingConfig(
            heartbeat_interval=settings.haxui_config.streaming.heartbeat_interval,
            chunk_size=settings.haxui_config.streaming.chunk_size,
            approval_poll_interval=settings.haxui_config.streaming.approval_poll_interval,
        )

        session = StreamingSession(
            runtime=runtime,
            conversation_store=store,
            conversation_id=conversation_id,
            entity_id=model,
            user_text=user_text,
            input_payload=input_payload,
            config=streaming_config,
        )

        return StreamingResponse(session.stream(), media_type="text/event-stream")

    return app


def extract_input_payload(request_payload: dict[str, Any]) -> dict[str, Any] | None:
    extra_body = request_payload.get("extra_body")
    if isinstance(extra_body, dict):
        input_data = extra_body.get("input_data")
        if isinstance(input_data, dict):
            return input_data
    return None


def extract_user_text(input_param: Any) -> str | None:
    if isinstance(input_param, str):
        return input_param
    if not isinstance(input_param, list):
        return None

    collected: list[str] = []
    for item in input_param:
        if not isinstance(item, dict):
            continue
        if item.get("type") != "message":
            continue
        contents = item.get("content")
        if not isinstance(contents, list):
            continue
        for content_item in contents:
            if isinstance(content_item, dict) and content_item.get("type") == "input_text":
                text = content_item.get("text")
                if isinstance(text, str):
                    collected.append(text)
    if not collected:
        return None
    return "\n\n".join(collected)


def is_simple_query(text: str) -> bool:
    """
    Detect if query is simple enough for optimized fast path.
    Uses same patterns as QueryRouterExecutor for consistency.
    """
    if not text or not isinstance(text, str):
        return False

    text_lower = text.lower().strip()

    # Trivial patterns from QueryRouterExecutor
    trivial_patterns = [
        r"^\d+\s*[+\-*/]\s*\d+$",  # Simple arithmetic: "1+1", "5*3"
        r"^(hi|hello|hey|greetings)\s*!*$",  # Greetings
        r"^what\s+is\s+\d+\s*[+\-*/]\s*\d+\??$",  # "what is 2+2?"
        r"^calculate\s+\d+\s*[+\-*/]\s*\d+$",  # "calculate 10/2"
        r"^what\s+is\s+the\s+(meaning|definition)\s+of\s+\w+\??$",  # Simple definitions
    ]

    for pattern in trivial_patterns:
        if re.match(pattern, text_lower):
            return True

    # Simple queries: short, no complex words
    if len(text.split()) <= 5:
        complex_indicators = [
            "analyze",
            "research",
            "investigate",
            "compare",
            "evaluate",
            "strategy",
            "plan",
            "design",
            "architecture",
            "system",
            "code",
            "implement",
            "create",
            "build",
            "develop",
        ]
        if not any(indicator in text_lower for indicator in complex_indicators):
            return True

    return False


def extract_approval_response(input_param: Any) -> dict[str, Any] | None:
    """
    Extract function_approval_response from OpenAI-format input.

    Returns dict with 'request_id', 'approved' keys if found, else None.
    """
    if not isinstance(input_param, list):
        return None

    for item in input_param:
        if not isinstance(item, dict):
            continue
        if item.get("type") != "message":
            continue
        contents = item.get("content")
        if not isinstance(contents, list):
            continue
        for content_item in contents:
            if (
                isinstance(content_item, dict)
                and content_item.get("type") == "function_approval_response"
            ):
                return {
                    "request_id": content_item.get("request_id"),
                    "approved": content_item.get("approved", False),
                }
            else:
                continue
    return None


# Instantiate application for ASGI servers.
app = create_app()
