"""Code interpreter tool with human-in-the-loop approval support."""

from agenticfleet.core.approval import ApprovalDecision, ApprovalHandler
from agenticfleet.core.cli_approval import create_approval_request
from agenticfleet.core.code_types import CodeExecutionResult
from agenticfleet.core.logging import get_logger

logger = get_logger(__name__)

# Global approval handler (set by workflow)
_approval_handler: ApprovalHandler | None = None


def set_approval_handler(handler: ApprovalHandler | None) -> None:
    """
    Set the global approval handler for code execution.

    Args:
        handler: Approval handler instance or None to disable approval
    """
    global _approval_handler
    _approval_handler = handler
    logger.info(f"Approval handler {'set' if handler else 'disabled'} for code execution")


def get_approval_handler() -> ApprovalHandler | None:
    """
    Get the current approval handler.

    Returns:
        Current approval handler or None
    """
    return _approval_handler


def _execute_without_approval(code: str, language: str) -> CodeExecutionResult:
    """Run the code interpreter without triggering approval requests."""

    if language != "python":
        return CodeExecutionResult(
            success=False,
            output="",
            error=(f"Language {language} not supported yet. Only Python is supported in Phase 1."),
            execution_time=0.0,
            language=language,
            exit_code=1,
        )

    from agenticfleet.agents.coder.tools.code_interpreter import _execute_python_code

    return _execute_python_code(code)


async def code_interpreter_tool_with_approval(
    code: str, language: str = "python"
) -> CodeExecutionResult:
    """Execute code with human-in-the-loop approval if enabled."""

    handler = get_approval_handler()

    if handler is None:
        return _execute_without_approval(code, language)

    request = create_approval_request(
        operation_type="code_execution",
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

    handler = get_approval_handler()

    if handler is None:
        return _execute_without_approval(code, language)

    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = None

    if loop is None:
        return asyncio.run(code_interpreter_tool_with_approval(code, language))

    if loop.is_running():
        logger.warning(
            "Approval handler is set but tool was called synchronously in running loop. "
            "Executing without approval."
        )
        return _execute_without_approval(code, language)

    return loop.run_until_complete(code_interpreter_tool_with_approval(code, language))
