"""Tests for the canonical CodeExecutionResult type."""

from pydantic import BaseModel

from agenticfleet.core import types as core_types
from agenticfleet.core.code_types import CodeExecutionResult as CodeExecutionResultModel


def test_code_execution_result_exports_match() -> None:
    """Both modules should expose the same Pydantic model class."""

    assert core_types.CodeExecutionResult is CodeExecutionResultModel
    assert issubclass(CodeExecutionResultModel, BaseModel)


def test_code_execution_result_serialisation() -> None:
    """Serialising the model should preserve the provided fields."""

    result = CodeExecutionResultModel(
        success=False,
        output="",
        error="not executed",
        execution_time=0.0,
        language="python",
        exit_code=1,
    )

    serialized = result.model_dump()
    assert serialized["language"] == "python"
    assert serialized["exit_code"] == 1
    assert serialized["success"] is False
