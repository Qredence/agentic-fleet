"""
Workflow as Agent with Reflection and Retry Pattern.

Copyright (c) Microsoft. All rights reserved.

This module demonstrates how to wrap a workflow as an agent using WorkflowAgent.
It uses a reflection pattern where a Worker executor generates responses and a
Reviewer executor evaluates them. If the response is not approved, the Worker
regenerates the output based on feedback until the Reviewer approves it. Only
approved responses are emitted to the external consumer. The workflow completes when idle.

Key Concepts:
- WorkflowAgent: Wraps a workflow to behave like a regular agent.
- Cyclic workflow design (Worker ↔ Reviewer) for iterative improvement.
- AgentRunUpdateEvent: Mechanism for emitting approved responses externally.
- Structured output parsing for review feedback using Pydantic.
- State management for pending requests and retry logic.

Example Usage:
    from agenticfleet.workflows.workflow_as_agent import create_workflow_agent, run_workflow_agent

    # Create and run the workflow agent
    await run_workflow_agent("Write code for parallel file processing.")

    # Or create the agent for integration with other systems
    agent = create_workflow_agent()
    async for event in agent.run_stream("Your query here"):
        print(event)
"""

import asyncio
from dataclasses import dataclass
from typing import Any
from uuid import uuid4

from agent_framework import (
    AgentRunResponseUpdate,
    AgentRunUpdateEvent,
    ChatClientProtocol,
    ChatMessage,
    Contents,
    Executor,
    Role,
    WorkflowBuilder,
    WorkflowContext,
    handler,
)
from agent_framework.openai import OpenAIChatClient
from pydantic import BaseModel


async def _emit_workflow_event(
    ctx: WorkflowContext[Any],
    executor_id: str,
    message: str,
    *,
    role: Role = Role.SYSTEM,
) -> None:
    """Emit workflow status updates as streaming events."""
    await ctx.add_event(
        AgentRunUpdateEvent(
            executor_id,
            data=AgentRunResponseUpdate(
                text=message,
                role=role,
                author_name=executor_id,
            ),
        )
    )


@dataclass
class ReviewRequest:
    """Structured request passed from Worker to Reviewer for evaluation."""

    request_id: str
    user_messages: list[ChatMessage]
    agent_messages: list[ChatMessage]


@dataclass
class ReviewResponse:
    """Structured response from Reviewer back to Worker."""

    request_id: str
    feedback: str
    approved: bool


class Reviewer(Executor):
    """
    Executor that reviews agent responses and provides structured feedback.

    The Reviewer evaluates responses against multiple quality criteria:
    - Relevance: Response addresses the query
    - Accuracy: Information is correct
    - Clarity: Response is easy to understand
    - Completeness: Response covers all aspects

    Only responses that meet all criteria are approved.
    """

    def __init__(self, id: str, chat_client: ChatClientProtocol) -> None:
        """
        Initialize the Reviewer executor.

        Args:
            id: Unique identifier for this executor
            chat_client: Chat client for LLM interactions
        """
        super().__init__(id=id)
        self._chat_client = chat_client

    @handler
    async def review(self, request: ReviewRequest, ctx: WorkflowContext[ReviewResponse]) -> None:
        """
        Review an agent response and provide structured feedback.

        Args:
            request: Review request containing messages to evaluate
            ctx: Workflow context for sending responses
        """
        status = f"Reviewer: Evaluating response for request {request.request_id[:8]}..."
        print(status)
        await _emit_workflow_event(ctx, self.id, status)

        # Define structured schema for the LLM to return.
        class _Response(BaseModel):
            feedback: str
            approved: bool

        # Construct review instructions and context.
        messages = [
            ChatMessage(
                role=Role.SYSTEM,
                text=(
                    "You are a reviewer for an AI agent. Provide feedback on the "
                    "exchange between a user and the agent. Indicate approval only if:\n"
                    "- Relevance: response addresses the query\n"
                    "- Accuracy: information is correct\n"
                    "- Clarity: response is easy to understand\n"
                    "- Completeness: response covers all aspects\n"
                    "Do not approve until all criteria are satisfied."
                ),
            )
        ]
        # Add conversation history.
        messages.extend(request.user_messages)
        messages.extend(request.agent_messages)

        # Add explicit review instruction.
        messages.append(ChatMessage(role=Role.USER, text="Please review the agent's responses."))

        status = "Reviewer: Sending review request to LLM..."
        print(status)
        await _emit_workflow_event(ctx, self.id, status)
        response = await self._chat_client.get_response(
            messages=messages, response_format=_Response
        )

        parsed = _Response.model_validate_json(response.messages[-1].text)

        status = f"Reviewer: Review complete - Approved: {parsed.approved}"
        print(status)
        await _emit_workflow_event(ctx, self.id, status)
        status = f"Reviewer: Feedback: {parsed.feedback}"
        print(status)
        await _emit_workflow_event(ctx, self.id, status)

        # Send structured review result to Worker.
        await ctx.send_message(
            ReviewResponse(
                request_id=request.request_id, feedback=parsed.feedback, approved=parsed.approved
            )
        )


class Worker(Executor):
    """
    Executor that generates responses and incorporates feedback when necessary.

    The Worker maintains state for pending requests to handle the retry cycle.
    When feedback is received, it regenerates responses incorporating the
    reviewer's suggestions until approval is achieved.
    """

    def __init__(self, id: str, chat_client: ChatClientProtocol) -> None:
        """
        Initialize the Worker executor.

        Args:
            id: Unique identifier for this executor
            chat_client: Chat client for LLM interactions
        """
        super().__init__(id=id)
        self._chat_client = chat_client
        self._pending_requests: dict[str, tuple[ReviewRequest, list[ChatMessage]]] = {}

    @handler
    async def handle_user_messages(
        self, user_messages: list[ChatMessage], ctx: WorkflowContext[ReviewRequest]
    ) -> None:
        """
        Handle incoming user messages and generate initial response.

        Args:
            user_messages: List of messages from the user
            ctx: Workflow context for sending review requests
        """
        status = "Worker: Received user messages, generating response..."
        print(status)
        await _emit_workflow_event(ctx, self.id, status)

        # Initialize chat with system prompt.
        messages = [ChatMessage(role=Role.SYSTEM, text="You are a helpful assistant.")]
        messages.extend(user_messages)

        status = "Worker: Calling LLM to generate response..."
        print(status)
        await _emit_workflow_event(ctx, self.id, status)
        response = await self._chat_client.get_response(messages=messages)
        response_text = response.messages[-1].text
        status = f"Worker: Response generated: {response_text}"
        print(status)
        await _emit_workflow_event(ctx, self.id, status)

        # Add agent messages to context.
        messages.extend(response.messages)

        # Create review request and send to Reviewer.
        request = ReviewRequest(
            request_id=str(uuid4()), user_messages=user_messages, agent_messages=response.messages
        )
        status = f"Worker: Sending response for review (ID: {request.request_id[:8]})"
        print(status)
        await _emit_workflow_event(ctx, self.id, status)
        await ctx.send_message(request)

        # Track request for possible retry.
        self._pending_requests[request.request_id] = (request, messages)

    @handler
    async def handle_review_response(
        self, review: ReviewResponse, ctx: WorkflowContext[ReviewRequest]
    ) -> None:
        """
        Handle review feedback and either emit approved response or regenerate.

        Args:
            review: Review response with approval status and feedback
            ctx: Workflow context for sending messages and events
        """
        status = (
            f"Worker: Received review for request {review.request_id[:8]} - "
            f"Approved: {review.approved}"
        )
        print(status)
        await _emit_workflow_event(ctx, self.id, status)

        if review.request_id not in self._pending_requests:
            raise ValueError(f"Unknown request ID in review: {review.request_id}")

        request, messages = self._pending_requests.pop(review.request_id)

        if review.approved:
            status = "Worker: Response approved. Emitting to external consumer..."
            print(status)
            await _emit_workflow_event(ctx, self.id, status)
            contents: list[Contents] = []
            for message in request.agent_messages:
                contents.extend(message.contents)

            # Emit approved result to external consumer via AgentRunUpdateEvent.
            await ctx.add_event(
                AgentRunUpdateEvent(
                    self.id, data=AgentRunResponseUpdate(contents=contents, role=Role.ASSISTANT)
                )
            )
            return

        status = f"Worker: Response not approved. Feedback: {review.feedback}"
        print(status)
        await _emit_workflow_event(ctx, self.id, status)
        status = "Worker: Regenerating response with feedback..."
        print(status)
        await _emit_workflow_event(ctx, self.id, status)

        # Incorporate review feedback.
        messages.append(ChatMessage(role=Role.SYSTEM, text=review.feedback))
        messages.append(
            ChatMessage(
                role=Role.SYSTEM,
                text="Please incorporate the feedback and regenerate the response.",
            )
        )
        messages.extend(request.user_messages)

        # Retry with updated prompt.
        response = await self._chat_client.get_response(messages=messages)
        response_text = response.messages[-1].text
        status = f"Worker: New response generated: {response_text}"
        print(status)
        await _emit_workflow_event(ctx, self.id, status)

        messages.extend(response.messages)

        # Send updated request for re-review.
        new_request = ReviewRequest(
            request_id=review.request_id,
            user_messages=request.user_messages,
            agent_messages=response.messages,
        )
        await ctx.send_message(new_request)

        # Track new request for further evaluation.
        self._pending_requests[new_request.request_id] = (new_request, messages)


def create_workflow_agent(
    worker_model: str = "gpt-4.1-nano",
    reviewer_model: str = "gpt-4.1",
    worker_id: str = "worker",
    reviewer_id: str = "reviewer",
) -> Any:
    """
    Create a workflow agent with Worker and Reviewer executors.

    This factory function creates a cyclic workflow where the Worker generates
    responses and the Reviewer evaluates them. The workflow continues until
    an approved response is generated.

    Args:
        worker_model: Model ID for the Worker's chat client
        reviewer_model: Model ID for the Reviewer's chat client
        worker_id: Unique identifier for the Worker executor
        reviewer_id: Unique identifier for the Reviewer executor

    Returns:
        WorkflowAgent: A workflow wrapped as an agent

    Example:
        agent = create_workflow_agent()
        async for event in agent.run_stream("Your query"):
            print(event)
    """
    # Initialize chat clients and executors.
    worker_client = OpenAIChatClient(model_id=worker_model)
    reviewer_client = OpenAIChatClient(model_id=reviewer_model)
    reviewer = Reviewer(id=reviewer_id, chat_client=reviewer_client)
    worker = Worker(id=worker_id, chat_client=worker_client)

    # Build workflow with Worker ↔ Reviewer cycle.
    agent = (
        WorkflowBuilder()
        .add_edge(worker, reviewer)  # Worker sends responses to Reviewer
        .add_edge(reviewer, worker)  # Reviewer provides feedback to Worker
        .set_start_executor(worker)
        .build()
        .as_agent()  # Wrap workflow as an agent
    )

    return agent


async def run_workflow_agent(
    query: str | None = None,
    worker_model: str = "gpt-4.1-nano",
    reviewer_model: str = "gpt-4.1",
    verbose: bool = True,
) -> None:
    """
    Run the workflow agent with a query.

    This is a convenience function that creates and runs the workflow agent
    in a single call. Useful for testing and simple use cases.

    Args:
        query: User query to process. If None, uses default example query.
        worker_model: Model ID for the Worker's chat client
        reviewer_model: Model ID for the Reviewer's chat client
        verbose: Whether to print progress messages

    Example:
        await run_workflow_agent("Write a function to sort a list")
    """
    if query is None:
        query = (
            "Write code for parallel reading 1 million files on disk and "
            "write to a sorted output file."
        )

    if verbose:
        print("Starting Workflow Agent Demo")
        print("=" * 50)
        print(f"Query: '{query}'")
        print("-" * 50)

    agent = create_workflow_agent(worker_model=worker_model, reviewer_model=reviewer_model)

    # Run agent in streaming mode to observe incremental updates.
    async for event in agent.run_stream(query):
        if verbose:
            print(f"Agent Response: {event}")

    if verbose:
        print("=" * 50)
        print("Workflow completed!")


async def main() -> None:
    """Main entry point for standalone execution."""
    print("Initializing Workflow as Agent Sample...")
    await run_workflow_agent()


if __name__ == "__main__":
    asyncio.run(main())
