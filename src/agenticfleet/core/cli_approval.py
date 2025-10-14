"""CLI-based approval handler for human-in-the-loop operations."""

import asyncio
import uuid
from functools import wraps
from typing import Any

from agenticfleet.core.approval import (
    ApprovalDecision,
    ApprovalHandler,
    ApprovalRequest,
    ApprovalResponse,
)
from agenticfleet.core.logging import get_logger

logger = get_logger(__name__)


class CLIApprovalHandler(ApprovalHandler):
    """CLI-based approval handler that prompts users in the terminal."""

    def __init_subclass__(cls, **kwargs: Any) -> None:  # pragma: no cover - class decoration logic
        super().__init_subclass__(**kwargs)

        base_request = CLIApprovalHandler.request_approval
        subclass_request = cls.request_approval

        if subclass_request is base_request:
            return

        @wraps(subclass_request)
        async def _wrapped_request(
            self: "CLIApprovalHandler", request: ApprovalRequest
        ) -> ApprovalResponse:
            response = await subclass_request(self, request)  # type: ignore[arg-type]
            self._record_approval_history(request, response)
            return response

        cls.request_approval = _wrapped_request  # type: ignore[assignment]

    def __init__(self, timeout_seconds: int = 300, auto_reject_on_timeout: bool = False):
        """
        Initialize CLI approval handler.

        Args:
            timeout_seconds: Maximum time to wait for approval (default: 300 seconds)
            auto_reject_on_timeout: Whether to auto-reject on timeout (default: False)
        """
        self.timeout_seconds = timeout_seconds
        self.auto_reject_on_timeout = auto_reject_on_timeout
        self.approval_history: list[tuple[ApprovalRequest, ApprovalResponse]] = []

    async def request_approval(self, request: ApprovalRequest) -> ApprovalResponse:
        """
        Request approval via CLI prompt.

        Args:
            request: The approval request with operation details

        Returns:
            ApprovalResponse: The user's decision and any modifications
        """
        logger.info(f"Approval requested for {request.operation_type} by {request.agent_name}")

        # Display approval prompt
        self._display_approval_request(request)

        # Get user input with timeout
        try:
            response = await asyncio.wait_for(
                self._get_user_input(request), timeout=self.timeout_seconds
            )
        except TimeoutError:
            logger.warning(
                f"Approval request {request.request_id} timed out after {self.timeout_seconds}s"
            )
            decision = (
                ApprovalDecision.REJECTED
                if self.auto_reject_on_timeout
                else ApprovalDecision.TIMEOUT
            )
            response = ApprovalResponse(
                request_id=request.request_id,
                decision=decision,
                modified_code=None,
                reason="Approval request timed out",
            )

        # Store in history
        self._record_approval_history(request, response)

        return response

    def _display_approval_request(self, request: ApprovalRequest) -> None:
        """Display the approval request in a formatted way."""
        print("\n" + "=" * 60)
        print("⚠️  APPROVAL REQUIRED")
        print("=" * 60)
        print(f"Agent:       {request.agent_name}")
        print(f"Operation:   {request.operation_type}")
        print(f"Description: {request.operation}")
        print(f"Request ID:  {request.request_id}")

        if request.code:
            print("\nCode to execute:")
            print("-" * 60)
            print(request.code)
            print("-" * 60)

        if request.details:
            print("\nAdditional details:")
            for key, value in request.details.items():
                print(f"  {key}: {value}")

        print("=" * 60)

    async def _get_user_input(self, request: ApprovalRequest) -> ApprovalResponse:
        """
        Get user input for approval decision.

        Args:
            request: The approval request

        Returns:
            ApprovalResponse: User's decision
        """
        loop = asyncio.get_event_loop()

        while True:
            # Run input in executor to avoid blocking
            user_input = await loop.run_in_executor(None, input, "\nApprove? (yes/no/edit): ")
            response_text = user_input.strip().lower()

            if response_text in ["yes", "y", "approve"]:
                return ApprovalResponse(
                    request_id=request.request_id,
                    decision=ApprovalDecision.APPROVED,
                    modified_code=None,
                    reason=None,
                )

            elif response_text in ["no", "n", "reject", "deny"]:
                reason = await loop.run_in_executor(
                    None, input, "Reason for rejection (optional): "
                )
                return ApprovalResponse(
                    request_id=request.request_id,
                    decision=ApprovalDecision.REJECTED,
                    modified_code=None,
                    reason=reason.strip() or "User rejected the operation",
                )

            elif response_text in ["edit", "modify", "e", "m"]:
                if not request.code:
                    print("⚠️  This operation cannot be modified (no code to edit)")
                    continue

                print("\nEnter modified code (press Ctrl+D or Ctrl+Z when done):")
                modified_lines = []
                try:
                    while True:
                        line = await loop.run_in_executor(None, input)
                        modified_lines.append(line)
                except EOFError:
                    pass

                modified_code = "\n".join(modified_lines).strip()
                if modified_code:
                    return ApprovalResponse(
                        request_id=request.request_id,
                        decision=ApprovalDecision.MODIFIED,
                        modified_code=modified_code,
                        reason="User modified the code",
                    )
                else:
                    print("⚠️  No modified code provided, please try again")
                    continue

            else:
                print("⚠️  Invalid input. Please enter 'yes', 'no', or 'edit' (or 'y', 'n', 'e')")
                continue

    def get_approval_history(self) -> list[tuple[ApprovalRequest, ApprovalResponse]]:
        """
        Get the history of all approval requests and responses.

        Returns:
            List of (request, response) tuples
        """
        return self.approval_history.copy()

    def _record_approval_history(
        self, request: ApprovalRequest, response: ApprovalResponse
    ) -> None:
        """Record approval interactions, avoiding duplicate entries."""

        entry = (request, response)
        if not self.approval_history or self.approval_history[-1] != entry:
            self.approval_history.append(entry)


def create_approval_request(
    operation_type: str,
    agent_name: str,
    operation: str,
    details: dict[str, Any] | None = None,
    code: str | None = None,
) -> ApprovalRequest:
    """
    Create an approval request with a unique ID.

    Args:
        operation_type: Type of operation (e.g., "code_execution")
        agent_name: Name of the agent requesting approval
        operation: Description of the operation
        details: Additional details about the operation
        code: Code to be executed (if applicable)

    Returns:
        ApprovalRequest: Configured approval request
    """
    return ApprovalRequest(
        request_id=str(uuid.uuid4()),
        operation_type=operation_type,
        agent_name=agent_name,
        operation=operation,
        details=details or {},
        code=code,
    )
