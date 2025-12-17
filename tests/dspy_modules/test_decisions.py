"""Tests for typed DSPy decision modules."""

from unittest.mock import MagicMock, patch

# Import decision modules
from agentic_fleet.dspy_modules.decisions import (
    QualityDecisionModule,
    RoutingDecisionModule,
    ToolPlanningModule,
    get_quality_module,
    get_routing_module,
    get_tool_planning_module,
)


class TestRoutingDecisionModule:
    """Tests for RoutingDecisionModule."""

    @patch("agentic_fleet.dspy_modules.decisions.routing.dspy")
    def test_routing_module_initialization(self, mock_dspy):
        """Test that RoutingDecisionModule initializes correctly."""
        # Mock dspy.TypedPredictor
        mock_predictor = MagicMock()
        mock_dspy.TypedPredictor.return_value = mock_predictor

        module = RoutingDecisionModule()

        assert module is not None
        assert hasattr(module, "predictor")
        assert module.predictor is mock_predictor

    @patch("agentic_fleet.dspy_modules.decisions.routing.dspy")
    def test_routing_module_forward(self, mock_dspy):
        """Test routing module forward pass."""
        # Mock predictor
        mock_predictor = MagicMock()
        mock_prediction = MagicMock()
        mock_predictor.return_value = mock_prediction
        mock_dspy.TypedPredictor.return_value = mock_predictor

        module = RoutingDecisionModule()
        result = module.forward(
            task="Test task",
            team="Test team",
            context="Test context",
            current_date="2025-01-01",
            available_tools="Tool1, Tool2",
        )

        assert result is mock_prediction
        mock_predictor.assert_called_once()


class TestToolPlanningModule:
    """Tests for ToolPlanningModule."""

    @patch("agentic_fleet.dspy_modules.decisions.tool_planning.dspy")
    def test_tool_planning_module_initialization(self, mock_dspy):
        """Test that ToolPlanningModule initializes correctly."""
        mock_predictor = MagicMock()
        mock_dspy.TypedPredictor.return_value = mock_predictor

        module = ToolPlanningModule()

        assert module is not None
        assert hasattr(module, "predictor")
        assert module.predictor is mock_predictor

    @patch("agentic_fleet.dspy_modules.decisions.tool_planning.dspy")
    def test_tool_planning_module_forward(self, mock_dspy):
        """Test tool planning module forward pass."""
        mock_predictor = MagicMock()
        mock_prediction = MagicMock()
        mock_predictor.return_value = mock_prediction
        mock_dspy.TypedPredictor.return_value = mock_predictor

        module = ToolPlanningModule()
        result = module.forward(
            task="Test task",
            available_tools="Tool1, Tool2",
            context="Test context",
        )

        assert result is mock_prediction
        mock_predictor.assert_called_once()


class TestQualityDecisionModule:
    """Tests for QualityDecisionModule."""

    @patch("agentic_fleet.dspy_modules.decisions.quality.dspy")
    def test_quality_module_initialization(self, mock_dspy):
        """Test that QualityDecisionModule initializes correctly."""
        mock_predictor = MagicMock()
        mock_dspy.TypedPredictor.return_value = mock_predictor

        module = QualityDecisionModule()

        assert module is not None
        assert hasattr(module, "predictor")
        assert module.predictor is mock_predictor

    @patch("agentic_fleet.dspy_modules.decisions.quality.dspy")
    def test_quality_module_forward(self, mock_dspy):
        """Test quality module forward pass."""
        mock_predictor = MagicMock()
        mock_prediction = MagicMock()
        mock_predictor.return_value = mock_prediction
        mock_dspy.TypedPredictor.return_value = mock_predictor

        module = QualityDecisionModule()
        result = module.forward(
            task="Test task",
            result="Test result",
        )

        assert result is mock_prediction
        mock_predictor.assert_called_once()


class TestModuleGetters:
    """Tests for module getter functions."""

    @patch("agentic_fleet.dspy_modules.decisions.routing.dspy")
    def test_get_routing_module_with_compiled(self, mock_dspy):
        """Test get_routing_module with pre-compiled module."""
        mock_compiled = MagicMock()

        module = get_routing_module(compiled_module=mock_compiled)

        assert module is mock_compiled

    @patch("agentic_fleet.dspy_modules.decisions.tool_planning.dspy")
    def test_get_tool_planning_module_with_compiled(self, mock_dspy):
        """Test get_tool_planning_module with pre-compiled module."""
        mock_compiled = MagicMock()

        module = get_tool_planning_module(compiled_module=mock_compiled)

        assert module is mock_compiled

    @patch("agentic_fleet.dspy_modules.decisions.quality.dspy")
    def test_get_quality_module_with_compiled(self, mock_dspy):
        """Test get_quality_module with pre-compiled module."""
        mock_compiled = MagicMock()

        module = get_quality_module(compiled_module=mock_compiled)

        assert module is mock_compiled

    @patch("agentic_fleet.dspy_modules.decisions.routing.dspy")
    @patch("agentic_fleet.dspy_modules.decisions.routing._MODULE_CACHE", {})
    def test_get_routing_module_fresh_creation(self, mock_dspy):
        """Test get_routing_module creates fresh module when not cached."""
        mock_predictor = MagicMock()
        mock_dspy.TypedPredictor.return_value = mock_predictor
        mock_dspy.Module = object  # Base class mock

        # First call should create new module
        module1 = get_routing_module()
        assert module1 is not None

        # Second call should return cached module
        module2 = get_routing_module()
        assert module2 is module1
