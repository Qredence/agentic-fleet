"""Simple manual test for HITL functionality without pytest."""

import asyncio

import pytest

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


@pytest.mark.asyncio
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


def main():
    """Run all tests."""
    print("=" * 60)
    print("HITL Manual Test Suite")
    print("=" * 60)

    try:
        test_create_approval_request()
        asyncio.run(test_mock_approval_handler())

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
