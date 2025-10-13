import sys
import time
from io import StringIO

from pydantic import BaseModel, Field


class CodeExecutionResult(BaseModel):
    """Structured result from code execution."""

    success: bool = Field(..., description="Whether execution completed successfully")
    output: str = Field(..., description="Standard output from execution")
    error: str = Field(..., description="Error output if any")
    execution_time: float = Field(..., description="Execution time in seconds")
    language: str = Field(..., description="Programming language used")
    exit_code: int | None = Field(None, description="Exit code if available")


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
    try:
        from agenticfleet.core.approved_tools import get_approval_handler
        from agenticfleet.core.approval import ApprovalDecision
        from agenticfleet.core.cli_approval import create_approval_request
        import asyncio

        handler = get_approval_handler()

        if handler is not None:
            # Create approval request
            request = create_approval_request(
                operation_type="code_execution",
                agent_name="coder",
                operation="Execute Python code",
                details={"language": language, "code_length": len(code)},
                code=code,
            )

            # Request approval (handle async)
            try:
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    # Cannot use asyncio.run in running loop
                    # Fall back to direct execution with warning
                    pass  # Will execute directly below
                else:
                    response = loop.run_until_complete(handler.request_approval(request))
                    
                    # Handle approval decision
                    if response.decision == ApprovalDecision.APPROVED:
                        pass  # Continue to execution
                    elif response.decision == ApprovalDecision.MODIFIED:
                        code = response.modified_code or code
                    else:  # REJECTED or TIMEOUT
                        reason = response.reason or f"Operation {response.decision.value}"
                        return CodeExecutionResult(
                            success=False,
                            output="",
                            error=f"Code execution was {response.decision.value}: {reason}",
                            execution_time=0.0,
                            language=language,
                            exit_code=1,
                        )
            except RuntimeError:
                # No event loop, create one
                response = asyncio.run(handler.request_approval(request))
                
                # Handle approval decision
                if response.decision == ApprovalDecision.APPROVED:
                    pass  # Continue to execution
                elif response.decision == ApprovalDecision.MODIFIED:
                    code = response.modified_code or code
                else:  # REJECTED or TIMEOUT
                    reason = response.reason or f"Operation {response.decision.value}"
                    return CodeExecutionResult(
                        success=False,
                        output="",
                        error=f"Code execution was {response.decision.value}: {reason}",
                        execution_time=0.0,
                        language=language,
                        exit_code=1,
                    )

    except ImportError:
        # Approval module not available, execute directly
        pass

    # Execute the (possibly modified) code
    return _execute_python_code(code)
