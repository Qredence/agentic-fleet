"""Web-based approval handler for HaxUI frontend integration.

This module provides an approval handler that works with SSE streaming,
allowing the frontend to display approval prompts and send responses.
"""

from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Any
from uuid import uuid4

from agenticfleet.core.approval import (
    ApprovalDecision,
    ApprovalHandler,
    ApprovalRequest,
    ApprovalResponse,
)

from .storage import SQLiteApprovalStore


class PendingApprovalRequest:
    """Container for a pending approval with async response handling."""

    def __init__(self, request: ApprovalRequest) -> None:
        self.request = request
        self.future: asyncio.Future[ApprovalResponse] = asyncio.Future()

    async def wait_for_response(self, timeout: float | None = None) -> ApprovalResponse:
        """Wait for approval response with optional timeout."""
        if timeout:
            return await asyncio.wait_for(self.future, timeout=timeout)
        return await self.future

    def set_response(self, response: ApprovalResponse) -> None:
        """Set the approval response, resolving the future."""
        if not self.future.done():
            self.future.set_result(response)


class WebApprovalHandler(ApprovalHandler):
    """Approval handler that emits events for web frontend consumption.

    This handler stores pending approval requests and waits for responses
    to be provided via set_approval_response(). It's designed to work with
    SSE streaming where the server emits approval events and waits for
    client responses.
    """

    def __init__(
        self, timeout_seconds: float = 300.0, store_path: Path | str | None = None
    ) -> None:
        """
        Initialize web approval handler.

        Args:
            timeout_seconds: Maximum time to wait for approval response
        """
        self.timeout_seconds = timeout_seconds
        self._pending: dict[str, PendingApprovalRequest] = {}
        self._lock = asyncio.Lock()
        self._store = SQLiteApprovalStore(store_path)
        self._store_initialised = asyncio.Event()

    async def initialise(self) -> None:
        """Initialise the backing store."""
        if self._store_initialised.is_set():
            return
        await self._store.initialise()
        self._store_initialised.set()

    async def request_approval(self, request: ApprovalRequest) -> ApprovalResponse:
        """
        Request approval and wait for web client response.

        Args:
            request: The approval request

        Returns:
            ApprovalResponse: The response from the web client

        Raises:
            asyncio.TimeoutError: If no response received within timeout
        """
        await self.initialise()
        async with self._lock:
            pending = PendingApprovalRequest(request)
            self._pending[request.request_id] = pending

        await self._store.add_request(
            {
                "request_id": request.request_id,
                "operation_type": request.operation_type,
                "agent_name": request.agent_name,
                "operation": request.operation,
                "details": request.details,
                "code": request.code,
                "timestamp": request.timestamp,
                "status": "pending",
            }
        )

        try:
            # Wait for response from web client
            response = await pending.wait_for_response(timeout=self.timeout_seconds)
            return response
        except TimeoutError:
            # Timeout - auto-reject
            return ApprovalResponse(
                request_id=request.request_id,
                decision=ApprovalDecision.TIMEOUT,
                reason=f"No response received within {self.timeout_seconds}s",
                modified_code=None,
            )
        finally:
            async with self._lock:
                self._pending.pop(request.request_id, None)
            await self._store.remove(request.request_id)

    async def set_approval_response(
        self,
        request_id: str,
        decision: ApprovalDecision,
        modified_code: str | None = None,
        reason: str | None = None,
    ) -> bool:
        """
        Provide a response to a pending approval request.

        Args:
            request_id: ID of the request to respond to
            decision: Approval decision
            modified_code: Modified code if decision is MODIFIED

        Returns:
            bool: True if request was found and response set, False otherwise
        """
        async with self._lock:
            pending = self._pending.get(request_id)

        if pending is None:
            store_updated = await self._store.mark_completed(
                request_id, decision.value, reason=reason
            )
            if store_updated:
                await self._store.remove(request_id)
            return store_updated

        response = ApprovalResponse(
            request_id=request_id,
            decision=decision,
            modified_code=modified_code,
            reason=reason,
        )
        pending.set_response(response)
        store_updated = await self._store.mark_completed(request_id, decision.value, reason=reason)
        if store_updated:
            await self._store.remove(request_id)
        return True

    async def get_pending_requests(self) -> list[dict[str, Any]]:
        """
        Get list of pending approval requests.

        Returns:
            List of pending requests as dictionaries
        """
        await self.initialise()
        pending = [
            {
                "request_id": req.request.request_id,
                "operation_type": req.request.operation_type,
                "agent_name": req.request.agent_name,
                "operation": req.request.operation,
                "details": req.request.details,
                "code": req.request.code,
                "timestamp": req.request.timestamp,
                "status": "pending",
                "reason": None,
            }
            for req in self._pending.values()
        ]
        stored = await self._store.list_pending()
        known_ids = {item["request_id"] for item in pending}
        for record in stored:
            if record["request_id"] not in known_ids:
                pending.append(record)
        return pending

    async def has_pending_requests(self) -> bool:
        """Check if there are any pending approval requests."""
        pending = await self.get_pending_requests()
        return len(pending) > 0


def create_approval_request(
    agent_name: str,
    operation_type: str,
    operation: str,
    details: dict[str, Any] | None = None,
) -> ApprovalRequest:
    """
    Helper to create approval requests with consistent formatting.

    Args:
        agent_name: Name of the agent making the request
        operation_type: Type of operation (e.g., "code_execution", "plan_review")
        operation: Human-readable operation description
        details: Additional context details

    Returns:
        ApprovalRequest ready to be sent to handler
    """
    return ApprovalRequest(
        request_id=uuid4().hex,
        agent_name=agent_name,
        operation_type=operation_type,
        operation=operation,
        details=details or {},
        code=None,
    )
