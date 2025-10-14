"""Tests for human-in-the-loop approval system."""

import asyncio

import pytest

from agenticfleet.core.approval import (
    ApprovalDecision,
    ApprovalRequest,
    ApprovalResponse,
)
from agenticfleet.core.cli_approval import CLIApprovalHandler, create_approval_request


class MockApprovalHandler(CLIApprovalHandler):
    """Mock approval handler for testing."""

    def __init__(self, decision: ApprovalDecision, modified_code: str | None = None):
        super().__init__(timeout_seconds=1, auto_reject_on_timeout=False)
        self.decision = decision
        self.modified_code = modified_code
        self.requests_received = []

    async def request_approval(self, request: ApprovalRequest) -> ApprovalResponse:
        """Mock approval that returns predefined decision."""
        self.requests_received.append(request)
        return ApprovalResponse(
            request_id=request.request_id,
            decision=self.decision,
            modified_code=self.modified_code,
            reason=f"Mock {self.decision.value}",
        )


def test_create_approval_request():
    """Test creating an approval request."""
    request = create_approval_request(
        operation_type="code_execution",
        agent_name="coder",
        operation="Execute Python code",
        details={"language": "python"},
        code="print('hello')",
    )

    assert request.operation_type == "code_execution"
    assert request.agent_name == "coder"
    assert request.operation == "Execute Python code"
    assert request.details["language"] == "python"
    assert request.code == "print('hello')"
    assert request.request_id  # Should have a UUID


@pytest.mark.asyncio
async def test_mock_approval_handler_approve():
    """Test mock approval handler with approval decision."""
    handler = MockApprovalHandler(decision=ApprovalDecision.APPROVED)

    request = create_approval_request(
        operation_type="code_execution",
        agent_name="coder",
        operation="Test operation",
        code="print('test')",
    )

    response = await handler.request_approval(request)

    assert response.decision == ApprovalDecision.APPROVED
    assert response.request_id == request.request_id
    assert len(handler.requests_received) == 1


@pytest.mark.asyncio
async def test_mock_approval_handler_reject():
    """Test mock approval handler with rejection decision."""
    handler = MockApprovalHandler(decision=ApprovalDecision.REJECTED)

    request = create_approval_request(
        operation_type="code_execution",
        agent_name="coder",
        operation="Test operation",
        code="print('test')",
    )

    response = await handler.request_approval(request)

    assert response.decision == ApprovalDecision.REJECTED
    assert response.reason == "Mock rejected"


@pytest.mark.asyncio
async def test_mock_approval_handler_modify():
    """Test mock approval handler with modification decision."""
    modified_code = "print('modified')"
    handler = MockApprovalHandler(
        decision=ApprovalDecision.MODIFIED, modified_code=modified_code
    )

    request = create_approval_request(
        operation_type="code_execution",
        agent_name="coder",
        operation="Test operation",
        code="print('original')",
    )

    response = await handler.request_approval(request)

    assert response.decision == ApprovalDecision.MODIFIED
    assert response.modified_code == modified_code


def test_approval_handler_should_require_approval():
    """Test the should_require_approval logic."""
    handler = MockApprovalHandler(decision=ApprovalDecision.APPROVED)

    # Should require approval for configured operations
    assert handler.should_require_approval(
        "code_execution", ["code_execution", "file_operations"]
    )
    assert handler.should_require_approval(
        "file_operations", ["code_execution", "file_operations"]
    )

    # Should not require approval for non-configured operations
    assert not handler.should_require_approval("web_search", ["code_execution"])


def test_approval_history():
    """Test that approval history is tracked."""
    handler = MockApprovalHandler(decision=ApprovalDecision.APPROVED)

    # Initially empty
    assert len(handler.get_approval_history()) == 0

    # Add a request
    request = create_approval_request(
        operation_type="test", agent_name="test", operation="test"
    )

    # Run async request
    loop = asyncio.get_event_loop()
    loop.run_until_complete(handler.request_approval(request))

    # Check history
    history = handler.get_approval_history()
    assert len(history) == 1
    assert history[0][0] == request
    assert history[0][1].decision == ApprovalDecision.APPROVED


def test_code_execution_with_approval():
    """Test code execution with approval integration."""
    from agenticfleet.agents.coder.tools.code_interpreter import (
        code_interpreter_tool,
    )
    from agenticfleet.core.approved_tools import set_approval_handler

    # Test without approval handler (should execute directly)
    set_approval_handler(None)
    result = code_interpreter_tool("print('no approval')", "python")
    assert result.success
    assert "no approval" in result.output

    # Test with approval handler that approves
    handler = MockApprovalHandler(decision=ApprovalDecision.APPROVED)
    set_approval_handler(handler)

    result = code_interpreter_tool("print('with approval')", "python")
    assert result.success
    assert "with approval" in result.output
    assert len(handler.requests_received) == 1

    # Test with approval handler that rejects
    handler = MockApprovalHandler(decision=ApprovalDecision.REJECTED)
    set_approval_handler(handler)

    result = code_interpreter_tool("print('rejected')", "python")
    assert not result.success
    assert "rejected" in result.error.lower()

    # Test with approval handler that modifies
    handler = MockApprovalHandler(
        decision=ApprovalDecision.MODIFIED, modified_code="print('modified output')"
    )
    set_approval_handler(handler)

    result = code_interpreter_tool("print('original')", "python")
    assert result.success
    assert "modified output" in result.output
    assert "original" not in result.output

    # Clean up
    set_approval_handler(None)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
