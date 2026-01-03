"""Unit tests for workflows/modules.py - pure functions only."""

import pytest
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

# Add src to path
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from agentic_fleet.workflows.modules import (
    _normalize_route_pattern,
    _extract_route_pattern,
    _is_complex,
    _is_simple,
    _is_direct,
)


class TestNormalizeRoutePattern:
    """Tests for _normalize_route_pattern function."""

    def test_direct_answer_maps_to_direct(self):
        """Test 'direct_answer' normalizes to 'direct'."""
        result = _normalize_route_pattern("direct_answer")
        assert result == "direct"

    def test_simple_tool_maps_to_simple(self):
        """Test 'simple_tool' normalizes to 'simple'."""
        result = _normalize_route_pattern("simple_tool")
        assert result == "simple"

    def test_complex_council_maps_to_complex(self):
        """Test 'complex_council' normalizes to 'complex'."""
        result = _normalize_route_pattern("complex_council")
        assert result == "complex"

    def test_already_normalized_unchanged(self):
        """Test that already normalized patterns pass through."""
        assert _normalize_route_pattern("direct") == "direct"
        assert _normalize_route_pattern("simple") == "simple"
        assert _normalize_route_pattern("complex") == "complex"

    def test_case_insensitive(self):
        """Test that normalization is case insensitive."""
        assert _normalize_route_pattern("DIRECT") == "direct"
        assert _normalize_route_pattern("Simple") == "simple"
        assert _normalize_route_pattern("COMPLEX") == "complex"

    def test_unknown_value_lowercased(self):
        """Test that unknown values are lowercased."""
        result = _normalize_route_pattern("SOMETHING")
        assert result == "something"


class TestExtractRoutePattern:
    """Tests for _extract_route_pattern function."""

    def _mock_response(self, additional_properties=None, full_conversation=None):
        """Create a mock AgentExecutorResponse that passes isinstance check."""
        mock = MagicMock()
        mock.agent_run_response.additional_properties = additional_properties or {}
        mock.full_conversation = full_conversation or []
        return mock

    def test_extracts_from_additional_properties(self):
        """Test extracting route_pattern from additional_properties."""
        mock = self._mock_response({"route_pattern": "complex"})
        with patch('agentic_fleet.workflows.modules.isinstance', return_value=True):
            result = _extract_route_pattern(mock)
            assert result == "complex"

    def test_extracts_simple_pattern(self):
        """Test extracting 'simple' pattern."""
        mock = self._mock_response({"route_pattern": "simple"})
        with patch('agentic_fleet.workflows.modules.isinstance', return_value=True):
            result = _extract_route_pattern(mock)
            assert result == "simple"

    def test_returns_empty_for_no_pattern(self):
        """Test returning empty string when no pattern found."""
        mock = self._mock_response({})
        with patch('agentic_fleet.workflows.modules.isinstance', return_value=True):
            result = _extract_route_pattern(mock)
            assert result == ""

    def test_falls_back_to_conversation_history(self):
        """Test fallback to conversation history for route_pattern."""
        mock_msg = MagicMock()
        mock_msg.additional_properties = {"route_pattern": "simple"}
        mock = self._mock_response({}, [mock_msg])
        with patch('agentic_fleet.workflows.modules.isinstance', return_value=True):
            result = _extract_route_pattern(mock)
            assert result == "simple"

    def test_extracts_from_text_routing_to(self):
        """Test extracting pattern from text containing 'routing to'."""
        mock_msg = MagicMock()
        mock_msg.additional_properties = None
        mock_msg.text = "Routing to Worker"
        mock = self._mock_response({}, [mock_msg])
        with patch('agentic_fleet.workflows.modules.isinstance', return_value=True):
            result = _extract_route_pattern(mock)
            assert result == "worker"

    def test_non_agent_executor_response_returns_empty(self):
        """Test that non-AgentExecutorResponse returns empty."""
        result = _extract_route_pattern("some string")
        assert result == ""

    def test_normalizes_pattern_during_extraction(self):
        """Test that extracted patterns are normalized."""
        mock = self._mock_response({"route_pattern": "direct_answer"})
        with patch('agentic_fleet.workflows.modules.isinstance', return_value=True):
            result = _extract_route_pattern(mock)
            assert result == "direct"


class TestIsComplex:
    """Tests for _is_complex function."""

    def _mock_response(self, pattern):
        mock = MagicMock()
        mock.agent_run_response.additional_properties = {"route_pattern": pattern}
        mock.full_conversation = []
        return mock

    def test_complex_returns_true(self):
        """Test is_complex returns True for complex pattern."""
        with patch('agentic_fleet.workflows.modules.isinstance', return_value=True):
            assert _is_complex(self._mock_response("complex")) is True

    def test_simple_returns_false(self):
        """Test is_complex returns False for simple pattern."""
        with patch('agentic_fleet.workflows.modules.isinstance', return_value=True):
            assert _is_complex(self._mock_response("simple")) is False

    def test_direct_returns_false(self):
        """Test is_complex returns False for direct pattern."""
        with patch('agentic_fleet.workflows.modules.isinstance', return_value=True):
            assert _is_complex(self._mock_response("direct")) is False

    def test_complex_council_normalizes(self):
        """Test that 'complex_council' normalizes to 'complex'."""
        with patch('agentic_fleet.workflows.modules.isinstance', return_value=True):
            assert _is_complex(self._mock_response("complex_council")) is True


class TestIsSimple:
    """Tests for _is_simple function."""

    def _mock_response(self, pattern):
        mock = MagicMock()
        mock.agent_run_response.additional_properties = {"route_pattern": pattern}
        mock.full_conversation = []
        return mock

    def test_simple_returns_true(self):
        """Test is_simple returns True for simple pattern."""
        with patch('agentic_fleet.workflows.modules.isinstance', return_value=True):
            assert _is_simple(self._mock_response("simple")) is True

    def test_complex_returns_false(self):
        """Test is_simple returns False for complex pattern."""
        with patch('agentic_fleet.workflows.modules.isinstance', return_value=True):
            assert _is_simple(self._mock_response("complex")) is False

    def test_direct_returns_false(self):
        """Test is_simple returns False for direct pattern."""
        with patch('agentic_fleet.workflows.modules.isinstance', return_value=True):
            assert _is_simple(self._mock_response("direct")) is False

    def test_simple_tool_normalizes(self):
        """Test that 'simple_tool' normalizes to 'simple'."""
        with patch('agentic_fleet.workflows.modules.isinstance', return_value=True):
            assert _is_simple(self._mock_response("simple_tool")) is True


class TestIsDirect:
    """Tests for _is_direct function."""

    def _mock_response(self, pattern):
        mock = MagicMock()
        mock.agent_run_response.additional_properties = {"route_pattern": pattern}
        mock.full_conversation = []
        return mock

    def test_direct_returns_true(self):
        """Test is_direct returns True for direct pattern."""
        with patch('agentic_fleet.workflows.modules.isinstance', return_value=True):
            assert _is_direct(self._mock_response("direct")) is True

    def test_simple_returns_false(self):
        """Test is_direct returns False for simple pattern."""
        with patch('agentic_fleet.workflows.modules.isinstance', return_value=True):
            assert _is_direct(self._mock_response("simple")) is False

    def test_complex_returns_false(self):
        """Test is_direct returns False for complex pattern."""
        with patch('agentic_fleet.workflows.modules.isinstance', return_value=True):
            assert _is_direct(self._mock_response("complex")) is False

    def test_direct_answer_normalizes(self):
        """Test that 'direct_answer' normalizes to 'direct'."""
        with patch('agentic_fleet.workflows.modules.isinstance', return_value=True):
            assert _is_direct(self._mock_response("direct_answer")) is True
