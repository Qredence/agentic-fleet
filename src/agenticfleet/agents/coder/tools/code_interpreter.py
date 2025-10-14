import sys
import time
from io import StringIO

# Import of CodeApprovalOutcome moved to local scope to avoid cyclic import.
from agenticfleet.core.code_types import CodeExecutionResult


def _execute_python_code(code: str) -> CodeExecutionResult:
    """
    Internal function to execute Python code.

    This is separated out so it can be called from both the original tool
    and the approval-wrapped version.
    """
    # Simple safe execution for Phase 1
    # In Phase 2, implement proper sandboxing with Docker
    start_time = time.time()

    # Capture output
    output_capture = StringIO()
    error_capture = StringIO()

    old_stdout = sys.stdout
    old_stderr = sys.stderr
    success = True
    execution_error = ""
    exit_code = 0

    try:
        # Redirect stdout and stderr
        sys.stdout = output_capture
        sys.stderr = error_capture

        # Execute the code with restricted globals for safety
        restricted_globals = {
            "__builtins__": {
                "print": print,
                "len": len,
                "str": str,
                "int": int,
                "float": float,
                "list": list,
                "dict": dict,
                "tuple": tuple,
                "set": set,
                "range": range,
                "enumerate": enumerate,
                "zip": zip,
                "min": min,
                "max": max,
                "sum": sum,
                "abs": abs,
                "round": round,
            }
        }

        exec(code, restricted_globals)

    except Exception as exc:
        success = False
        execution_error = f"Execution error: {exc}"
        exit_code = 1

    finally:
        sys.stdout = old_stdout
        sys.stderr = old_stderr

    output = output_capture.getvalue()
    error_output = error_capture.getvalue().strip()
    execution_time = time.time() - start_time

    if execution_error:
        combined_error = "\n".join(part for part in [error_output, execution_error] if part).strip()
    else:
        combined_error = error_output

    return CodeExecutionResult(
        success=success,
        output=output,
        error=combined_error,
        execution_time=execution_time,
        language="python",
        exit_code=exit_code,
    )


def code_interpreter_tool(code: str, language: str = "python") -> CodeExecutionResult:
    """
    Execute code in a safe environment and return structured results.

    This tool checks for an approval handler and requests approval if configured.

    Args:
        code: The code to execute
        language: Programming language (currently supports python)

    Returns:
        CodeExecutionResult: Structured execution results with success status and outputs
    """
    if language != "python":
        return CodeExecutionResult(
            success=False,
            output="",
            error=f"Language {language} not supported yet. Only Python is supported in Phase 1.",
            execution_time=0.0,
            language=language,
            exit_code=1,
        )

    # Check if approval is required
    from agenticfleet.core.code_execution_approval import (
        maybe_request_approval_for_code_execution,
    )

    approval_result = maybe_request_approval_for_code_execution(code, language)
    if approval_result.outcome == CodeApprovalOutcome.REJECTED:
        if approval_result.execution_result is not None:
            return approval_result.execution_result
        # If no execution result, fall through to execute anyway (shouldn't happen)

    # Use modified code if provided, otherwise original code
    code_to_execute = approval_result.modified_code or code

    # Execute the (possibly modified) code
    return _execute_python_code(code_to_execute)
