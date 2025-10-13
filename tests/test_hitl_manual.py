"""Simple manual test for HITL functionality without pytest."""

import asyncio

from agenticfleet.core.approval import ApprovalDecision
from agenticfleet.core.cli_approval import create_approval_request


class MockApprovalHandler:
    """Mock approval handler for testing."""

    def __init__(self, decision: ApprovalDecision, modified_code: str | None = None):
        self.decision = decision
        self.modified_code = modified_code
        self.requests_received = []

    async def request_approval(self, request):
        """Mock approval that returns predefined decision."""
        from agenticfleet.core.approval import ApprovalResponse

        self.requests_received.append(request)
        return ApprovalResponse(
            request_id=request.request_id,
            decision=self.decision,
            modified_code=self.modified_code,
            reason=f"Mock {self.decision.value}",
        )


def test_create_approval_request():
    """Test creating an approval request."""
    print("Test: create_approval_request")
    request = create_approval_request(
        operation_type="code_execution",
        agent_name="coder",
        operation="Execute Python code",
        details={"language": "python"},
        code="print('hello')",
    )

    assert request.operation_type == "code_execution"
    assert request.agent_name == "coder"
    assert request.code == "print('hello')"
    print("  ✓ Request created successfully")


async def test_mock_approval_handler():
    """Test mock approval handler."""
    print("\nTest: mock_approval_handler")

    # Test approval
    handler = MockApprovalHandler(decision=ApprovalDecision.APPROVED)
    request = create_approval_request(
        operation_type="code_execution",
        agent_name="coder",
        operation="Test operation",
        code="print('test')",
    )

    response = await handler.request_approval(request)
    assert response.decision == ApprovalDecision.APPROVED
    print("  ✓ Approval works")

    # Test rejection
    handler = MockApprovalHandler(decision=ApprovalDecision.REJECTED)
    response = await handler.request_approval(request)
    assert response.decision == ApprovalDecision.REJECTED
    print("  ✓ Rejection works")

    # Test modification
    handler = MockApprovalHandler(
        decision=ApprovalDecision.MODIFIED, modified_code="print('modified')"
    )
    response = await handler.request_approval(request)
    assert response.decision == ApprovalDecision.MODIFIED
    assert response.modified_code == "print('modified')"
    print("  ✓ Modification works")


def test_code_execution_integration():
    """Test code execution with approval integration."""
    print("\nTest: code_execution_integration")

    from agenticfleet.agents.coder.tools.code_interpreter import code_interpreter_tool
    from agenticfleet.core.approved_tools import set_approval_handler

    # Test without approval handler
    set_approval_handler(None)
    result = code_interpreter_tool("print('no approval')", "python")
    assert result.success
    assert "no approval" in result.output
    print("  ✓ Direct execution (no handler)")

    # Test with approval handler that approves
    handler = MockApprovalHandler(decision=ApprovalDecision.APPROVED)
    set_approval_handler(handler)

    result = code_interpreter_tool("print('with approval')", "python")
    assert result.success
    assert "with approval" in result.output
    assert len(handler.requests_received) == 1
    print("  ✓ Execution with approval")

    # Test with approval handler that rejects
    handler = MockApprovalHandler(decision=ApprovalDecision.REJECTED)
    set_approval_handler(handler)

    result = code_interpreter_tool("print('rejected')", "python")
    assert not result.success
    assert "rejected" in result.error.lower()
    print("  ✓ Rejection blocks execution")

    # Test with approval handler that modifies
    handler = MockApprovalHandler(
        decision=ApprovalDecision.MODIFIED, modified_code="print('modified output')"
    )
    set_approval_handler(handler)

    result = code_interpreter_tool("print('original')", "python")
    assert result.success
    assert "modified output" in result.output
    print("  ✓ Modification changes code")

    # Clean up
    set_approval_handler(None)


def main():
    """Run all tests."""
    print("=" * 60)
    print("HITL Manual Test Suite")
    print("=" * 60)

    try:
        test_create_approval_request()
        asyncio.run(test_mock_approval_handler())
        test_code_execution_integration()

        print("\n" + "=" * 60)
        print("✓ All tests passed!")
        print("=" * 60)
        return 0
    except AssertionError as e:
        print(f"\n✗ Test failed: {e}")
        return 1
    except Exception as e:
        print(f"\n✗ Unexpected error: {e}")
        import traceback

        traceback.print_exc()
        return 1


if __name__ == "__main__":
    import sys

    sys.exit(main())
