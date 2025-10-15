#!/usr/bin/env python
"""Manual demo of HITL approval system."""

import asyncio
import sys

from agenticfleet.core.approval import ApprovalDecision, ApprovalRequest, ApprovalResponse
from agenticfleet.core.approved_tools import set_approval_handler
from agenticfleet.core.cli_approval import CLIApprovalHandler, create_approval_request


async def demo_approval_prompt() -> None:
    """Demo the approval prompt interface."""
    print("\n" + "=" * 70)
    print("DEMO: HITL Approval Prompt")
    print("=" * 70)

    # Create a handler
    handler = CLIApprovalHandler(timeout_seconds=60, auto_reject_on_timeout=False)

    # Create a sample request
    request = create_approval_request(
        operation_type="code_execution",
        agent_name="coder",
        operation="Execute Python code to calculate fibonacci",
        details={"language": "python", "safe": True},
        code="""def fib(n):
    a, b = 0, 1
    for _ in range(n):
        print(a, end=' ')
        a, b = b, a + b
    print()

fib(10)""",
    )

    # Request approval
    print("\nThis will show the approval prompt...")
    print("Try: 'yes', 'no', or 'edit'")
    print()

    response = await handler.request_approval(request)

    print("\n" + "=" * 70)
    print(f"Decision: {response.decision.value}")
    if response.modified_code:
        print(f"Modified code: {response.modified_code[:50]}...")
    if response.reason:
        print(f"Reason: {response.reason}")
    print("=" * 70)


def demo_code_execution_with_approval() -> None:
    """Demo code execution with approval."""
    print("\n" + "=" * 70)
    print("DEMO: Code Execution with Approval")
    print("=" * 70)

    # Simple approval handler that auto-approves for demo
    class AutoApproveHandler(CLIApprovalHandler):
        async def request_approval(self, request: ApprovalRequest) -> ApprovalResponse:
            from agenticfleet.core.approval import ApprovalResponse

            print(f"\n[Auto-Approved] {request.operation}")
            return ApprovalResponse(
                request_id=request.request_id,
                decision=ApprovalDecision.APPROVED,
                modified_code=None,
                reason="Demo auto-approval",
            )

    handler = AutoApproveHandler()
    set_approval_handler(handler)

    # Execute code with approval (tool removed, showing approval flow)
    print("\nExecuting code with approval handler...")
    print("Note: Code interpreter tool has been removed from this demo.")
    print("Approval system would have prompted here.")

    # Mock result for demo
    from agenticfleet.core.code_types import CodeExecutionResult

    result = CodeExecutionResult(
        success=False,
        output="",
        error="Code interpreter tool removed",
        execution_time=0.0,
        language="python",
        exit_code=1,
    )

    print("\nExecution result:")
    print(f"  Success: {result.success}")
    print(f"  Output: {result.output}")
    print(f"  Time: {result.execution_time:.3f}s")

    # Clean up
    set_approval_handler(None)

    print("=" * 70)


def main() -> None:
    """Run demos."""
    print("\n" + "=" * 70)
    print("AgenticFleet - Human-in-the-Loop Demo")
    print("=" * 70)

    print("\nThis demo shows how the HITL approval system works.")
    print("You can test the approval flow interactively.")

    if len(sys.argv) > 1 and sys.argv[1] == "--interactive":
        # Interactive mode - show real approval prompt
        print("\n[Interactive Mode]")
        asyncio.run(demo_approval_prompt())
    else:
        # Non-interactive mode - just show auto-approval
        print("\n[Non-Interactive Mode]")
        print("Run with --interactive to see the real approval prompt")
        demo_code_execution_with_approval()

    print("\n✓ Demo completed!")
    print("\nTo use HITL in production:")
    print("  1. Ensure 'human_in_the_loop.enabled: true' in config/workflow.yaml")
    print("  2. Run: python -m agenticfleet")
    print("  3. Try: 'Write and execute code to calculate fibonacci numbers'")
    print()


if __name__ == "__main__":
    main()
