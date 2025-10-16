"""Code interpreter tool with human-in-the-loop approval support."""

from collections.abc import Iterable

from agenticfleet.core.approval import ApprovalDecision, ApprovalHandler
from agenticfleet.core.cli_approval import create_approval_request
from agenticfleet.core.code_types import CodeExecutionResult
from agenticfleet.core.logging import get_logger

logger = get_logger(__name__)

# Global approval handler (set by workflow)
_approval_handler: ApprovalHandler | None = None
_required_operations: set[str] = set()
_trusted_operations: set[str] = set()


def set_approval_handler(
    handler: ApprovalHandler | None,
    *,
    require_operations: Iterable[str] | None = None,
    trusted_operations: Iterable[str] | None = None,
) -> None:
    """
    Set the global approval handler for code execution and configure approval requirements.

    Args:
        handler: Approval handler instance or None to disable approval.
        require_operations: Iterable of operation identifiers (str) that require approval.
            Each operation is normalized (stripped and lowercased). If None or empty, no operations require approval.
        trusted_operations: Iterable of operation identifiers (str) that are always allowed without approval.
            Each operation is normalized (stripped and lowercased). If an operation appears in both
            require_operations and trusted_operations, trusted_operations takes precedence and approval is not required.

    Notes:
        - Passing handler=None disables approval and resets required/trusted operations.
        - trusted_operations always override require_operations for the same operation.
    """
    global _approval_handler
    global _required_operations
    global _trusted_operations

    _approval_handler = handler

    if handler is None:
        _required_operations = set()
        _trusted_operations = set()
        logger.info("Approval handler disabled for code execution")
        return

    _required_operations = {op.strip().lower() for op in (require_operations or []) if op.strip()}
    _trusted_operations = {op.strip().lower() for op in (trusted_operations or []) if op.strip()}
    logger.info("Approval handler configured for code execution")


def get_approval_handler() -> ApprovalHandler | None:
    """
    Get the current approval handler.

    Returns:
        Current approval handler or None
    """
    return _approval_handler


def operation_requires_approval(operation_type: str) -> bool:
    """
    Determine whether the given operation should request approval.

    Args:
        operation_type: Operation identifier (e.g., ``code_execution``).

    Returns:
        True if approval is required, False otherwise.
    """

    if operation_type.lower() in _trusted_operations:
        return False

    if not _required_operations:
        return False

    return operation_type.lower() in _required_operations


def _execute_without_approval(code: str, language: str) -> CodeExecutionResult:
    """Run the code interpreter without triggering approval requests."""

    return CodeExecutionResult(
        success=False,
        output="",
        error="Code interpreter tool has been removed.",
        execution_time=0.0,
        language=language,
        exit_code=1,
    )


async def code_interpreter_tool_with_approval(
    code: str, language: str = "python"
) -> CodeExecutionResult:
    """Execute code with human-in-the-loop approval if enabled."""

    operation_type = "code_execution"
    handler = get_approval_handler()

    if handler is None or not operation_requires_approval(operation_type):
        return _execute_without_approval(code, language)

    request = create_approval_request(
        operation_type=operation_type,
        agent_name="coder",
        operation="Execute Python code",
        details={"language": language, "code_length": len(code)},
        code=code,
    )

    logger.info("Requesting approval for code execution: %s", request.request_id)
    response = await handler.request_approval(request)

    if response.decision == ApprovalDecision.APPROVED:
        logger.info("Code execution approved: %s", request.request_id)
        return _execute_without_approval(code, language)

    if response.decision == ApprovalDecision.MODIFIED:
        logger.info("Code execution approved with modifications: %s", request.request_id)
        modified_code = response.modified_code or code
        return _execute_without_approval(modified_code, language)

    logger.warning("Code execution %s: %s", response.decision.value, request.request_id)
    reason = response.reason or f"Operation {response.decision.value}"
    return CodeExecutionResult(
        success=False,
        output="",
        error=f"Code execution was {response.decision.value}: {reason}",
        execution_time=0.0,
        language=language,
        exit_code=1,
    )


# For synchronous contexts, provide a sync wrapper
def code_interpreter_tool(code: str, language: str = "python") -> CodeExecutionResult:
    """Synchronous wrapper for code execution with approval."""

    import asyncio

    operation_type = "code_execution"
    handler = get_approval_handler()

    if handler is None or not operation_requires_approval(operation_type):
        return _execute_without_approval(code, language)

    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        # No running loop, safe to create a new one
        return asyncio.run(code_interpreter_tool_with_approval(code, language))

    if loop.is_running():
        logger.warning(
            "Approval handler is set but tool was called synchronously in running loop. "
            "Executing without approval."
        )
        return _execute_without_approval(code, language)

    return loop.run_until_complete(code_interpreter_tool_with_approval(code, language))
