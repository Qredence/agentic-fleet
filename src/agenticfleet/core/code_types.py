"""Core type definitions for code execution results."""

from pydantic import BaseModel, ConfigDict, Field


class CodeExecutionResult(BaseModel):
    """Structured payload describing the outcome of executing a code snippet."""

    success: bool = Field(
        ..., description="True when the code finished without raising an exception."
    )
    output: str = Field(
        "",
        description="Captured standard output produced while running the snippet.",
    )
    error: str = Field(
        "",
        description="Combined standard error stream and any synthesized error message.",
    )
    execution_time: float = Field(
        0.0,
        ge=0.0,
        description="Elapsed runtime in seconds for the execution attempt.",
    )
    language: str = Field(..., description="Programming language the snippet was executed with.")
    exit_code: int = Field(..., description="Process-style exit code; zero indicates success.")

    model_config = ConfigDict(extra="forbid", populate_by_name=True)
