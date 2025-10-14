"""Type definitions for code execution results."""

from pydantic import BaseModel, Field


class CodeExecutionResult(BaseModel):
    """Result of code execution."""

    success: bool = Field(..., description="Whether the code executed successfully")
    output: str = Field(default="", description="Standard output from the execution")
    error: str = Field(default="", description="Error output from the execution")
    execution_time: float = Field(..., description="Execution time in seconds")
    language: str = Field(..., description="Programming language used")
    exit_code: int = Field(default=0, description="Exit code from execution")
