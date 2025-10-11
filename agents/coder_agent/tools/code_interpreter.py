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


def code_interpreter_tool(code: str, language: str = "python") -> CodeExecutionResult:
    """
    Execute code in a safe environment and return structured results.

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
        )

    # Simple safe execution for Phase 1
    # In Phase 2, implement proper sandboxing with Docker
    start_time = time.time()

    # Capture output
    output_capture = StringIO()
    error_capture = StringIO()

    try:
        # Redirect stdout and stderr
        old_stdout = sys.stdout
        old_stderr = sys.stderr
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

        # Restore stdout/stderr
        sys.stdout = old_stdout
        sys.stderr = old_stderr

        output = output_capture.getvalue()
        error = error_capture.getvalue()
        execution_time = time.time() - start_time

        return CodeExecutionResult(
            success=True,
            output=output,
            error=error,
            execution_time=execution_time,
            language=language,
            exit_code=0,  # Assuming successful execution has an exit code of 0
        )

    except Exception as e:
        # Restore stdout/stderr in case of error
        sys.stdout = old_stdout
        sys.stderr = old_stderr

        execution_time = time.time() - start_time

        return CodeExecutionResult(
            success=False,
            output=output_capture.getvalue(),
            error=f"Execution error: {str(e)}",
            execution_time=execution_time,
            language=language,
            exit_code=1,  # Assuming failed execution has an exit code of 1
        )
