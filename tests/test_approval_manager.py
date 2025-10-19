"""Test the approved_tools module-level approval functions."""

from unittest.mock import MagicMock

from agenticfleet.core.approval import ApprovalHandler
from agenticfleet.core.approved_tools import (
    get_approval_handler,
    operation_requires_approval,
    set_approval_handler,
)


def test_approval_handler_initialization() -> None:
    """Test initial state has no approval handler."""
    set_approval_handler(None)
    assert get_approval_handler() is None
    assert not operation_requires_approval("code_execution")


def test_set_approval_handler_with_none() -> None:
    """Test setting None handler disables approval."""
    set_approval_handler(None)
    assert get_approval_handler() is None
    assert not operation_requires_approval("code_execution")
    assert not operation_requires_approval("file_system")


def test_operation_requires_approval() -> None:
    """Test that operations can be marked as requiring approval."""
    mock_handler = MagicMock(spec=ApprovalHandler)
    set_approval_handler(mock_handler, require_operations=["code_execution"])

    assert get_approval_handler() is mock_handler
    assert operation_requires_approval("code_execution")
    assert not operation_requires_approval("file_system")

    # Cleanup
    set_approval_handler(None)


def test_trusted_operations_override_required() -> None:
    """Test that trusted operations override required operations."""
    mock_handler = MagicMock(spec=ApprovalHandler)
    set_approval_handler(
        mock_handler,
        require_operations=["code_execution"],
        trusted_operations=["code_execution"],
    )

    # Even though code_execution is in require_operations,
    # it's also in trusted_operations so approval is NOT required
    assert not operation_requires_approval("code_execution")

    # Cleanup
    set_approval_handler(None)


def test_case_insensitive_operations() -> None:
    """Test that operation names are normalized (case-insensitive)."""
    mock_handler = MagicMock(spec=ApprovalHandler)
    set_approval_handler(mock_handler, require_operations=["Code_Execution"])

    # Should match regardless of case
    assert operation_requires_approval("code_execution")
    assert operation_requires_approval("CODE_EXECUTION")
    assert operation_requires_approval("Code_Execution")

    # Cleanup
    set_approval_handler(None)
