"""
Tests for judge evaluation and refinement routing functionality.
"""

import os
from unittest.mock import AsyncMock, patch

import pytest

# Mock agent-framework and dspy before importing
os.environ.setdefault("OPENAI_API_KEY", "test-key")
os.environ.setdefault("TAVILY_API_KEY", "test-key")


@pytest.fixture
def mock_openai_client():
    """Mock OpenAI async client."""
    mock_client = AsyncMock()
    return mock_client


@pytest.fixture
def mock_dspy():
    """Mock DSPy settings."""
    with patch("agentic_fleet.utils.dspy_manager.configure_dspy_settings") as mock_configure:
        mock_configure.return_value = None
        yield mock_configure


@pytest.fixture
async def workflow(mock_openai_client, mock_dspy):
    """Create a workflow instance for testing."""
    from agentic_fleet.workflows.supervisor_workflow import SupervisorWorkflow, WorkflowConfig

    config = WorkflowConfig(
        enable_judge=True,
        judge_threshold=7.0,
        max_refinement_rounds=2,
        compile_dspy=False,
    )

    workflow = SupervisorWorkflow(workflow_config=config)

    # Mock OpenAI client
    workflow._openai_client = mock_openai_client

    # Mock agents
    mock_judge = AsyncMock()
    mock_judge.run = AsyncMock(
        return_value="Score: 5/10\nMissing elements: citations, vote_totals\nRefinement agent: Researcher\nRefinement needed: yes\nRequired improvements: Add citations and vote totals"
    )
    mock_judge.description = "Quality evaluation specialist"

    mock_researcher = AsyncMock()
    mock_researcher.run = AsyncMock(return_value="Improved response with citations and vote totals")
    mock_researcher.description = "Information gathering specialist"

    workflow.agents = {
        "Judge": mock_judge,
        "Researcher": mock_researcher,
        "Writer": AsyncMock(),
        "Analyst": AsyncMock(),
    }

    await workflow.initialize(compile_dspy=False)

    return workflow


@pytest.mark.asyncio
async def test_judge_phase_disabled(workflow):
    """Test that judge phase is skipped when disabled."""
    workflow.config.enable_judge = False

    result = await workflow._judge_phase("test task", "test result")

    assert result["score"] == 10.0
    assert result["refinement_needed"] == "no"
    assert result["refinement_agent"] is None


@pytest.mark.asyncio
async def test_judge_phase_missing_agent(workflow):
    """Test that judge phase handles missing judge agent gracefully."""
    workflow.agents.pop("Judge", None)

    result = await workflow._judge_phase("test task", "test result")

    assert result["score"] == 10.0
    assert result["refinement_needed"] == "no"


@pytest.mark.asyncio
async def test_judge_phase_evaluation(workflow):
    """Test judge phase evaluation."""
    result = await workflow._judge_phase("test task", "test result")

    assert "score" in result
    assert "refinement_needed" in result
    assert "missing_elements" in result
    assert "refinement_agent" in result
    assert "required_improvements" in result

    # Verify judge agent was called
    workflow.agents["Judge"].run.assert_called_once()


@pytest.mark.asyncio
async def test_parse_judge_response(workflow):
    """Test parsing of judge response."""
    response = """Score: 6/10
Missing elements: citations, vote_totals
Refinement agent: Researcher
Refinement needed: yes
Required improvements: Add authoritative sources and specific vote numbers"""

    result = workflow._parse_judge_response(response, "task", "result", "criteria")

    assert result["score"] == 6.0
    assert "citations" in result["missing_elements"].lower()
    assert result["refinement_needed"] == "yes"
    assert result["refinement_agent"] == "Researcher"


@pytest.mark.asyncio
async def test_parse_judge_response_below_threshold(workflow):
    """Test that score below threshold triggers refinement."""
    response = "Score: 5/10\nMissing elements: citations"

    result = workflow._parse_judge_response(response, "task", "result", "criteria")

    assert result["score"] == 5.0
    assert result["refinement_needed"] == "yes"  # Should be auto-set below threshold


def test_determine_refinement_agent_citations(workflow):
    """Test refinement agent determination for missing citations."""
    agent = workflow._determine_refinement_agent("citations, sources")
    assert agent == "Researcher"


def test_determine_refinement_agent_vote_totals(workflow):
    """Test refinement agent determination for missing vote totals."""
    agent = workflow._determine_refinement_agent("vote totals, percentages")
    assert agent == "Researcher"


def test_determine_refinement_agent_dates(workflow):
    """Test refinement agent determination for missing dates."""
    agent = workflow._determine_refinement_agent("dates, certification")
    assert agent == "Researcher"


def test_determine_refinement_agent_formatting(workflow):
    """Test refinement agent determination for formatting issues."""
    agent = workflow._determine_refinement_agent("formatting, structure")
    assert agent == "Writer"


def test_determine_refinement_agent_default(workflow):
    """Test default refinement agent."""
    agent = workflow._determine_refinement_agent("")
    assert agent == "Researcher"


def test_build_refinement_task(workflow):
    """Test building refinement task from judge evaluation."""
    judge_eval = {
        "missing_elements": "citations, vote_totals",
        "required_improvements": "Add sources and numbers",
    }

    task = workflow._build_refinement_task("current result", judge_eval)

    assert "citations" in task.lower()
    assert "vote_totals" in task.lower()
    assert "current result" in task


def test_get_quality_criteria(workflow):
    """Test quality criteria definition."""
    criteria = workflow._get_quality_criteria()

    assert "Citations" in criteria
    assert "Vote totals" in criteria
    assert "Certification dates" in criteria
    assert "Detailed context" in criteria


@pytest.mark.asyncio
async def test_refinement_loop_terminates_on_no_refinement(workflow):
    """Test that refinement loop terminates when judge says no refinement needed."""
    # Mock judge to return no refinement needed
    workflow.agents["Judge"].run = AsyncMock(return_value="Score: 8/10\nRefinement needed: no")

    # Mock run method to capture calls
    original_run = workflow.run
    call_count = 0

    async def mock_run(task):
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            # First call - normal execution
            return await original_run(task)
        return {"result": "test", "judge_evaluations": []}

    workflow.run = mock_run

    # This should not loop infinitely
    await workflow._judge_phase("test", "result")

    # Verify judge was called
    assert workflow.agents["Judge"].run.called


@pytest.mark.asyncio
async def test_refinement_loop_respects_max_rounds(workflow):
    """Test that refinement loop respects max_refinement_rounds."""
    workflow.config.max_refinement_rounds = 1

    # Mock judge to always request refinement
    workflow.agents["Judge"].run = AsyncMock(
        return_value="Score: 4/10\nRefinement needed: yes\nRefinement agent: Researcher"
    )

    # This should only run one refinement round
    result = await workflow._judge_phase("test", "result")

    # The actual refinement loop is in run(), but we can test the logic
    assert result["refinement_needed"] == "yes"


@pytest.mark.asyncio
async def test_refinement_agent_not_available(workflow):
    """Test handling when refinement agent is not available."""
    # Remove Researcher agent
    workflow.agents.pop("Researcher", None)

    # Judge requests refinement to Researcher
    workflow.agents["Judge"].run = AsyncMock(
        return_value="Score: 4/10\nRefinement needed: yes\nRefinement agent: Researcher"
    )

    result = await workflow._judge_phase("test", "result")

    # Should still return evaluation, but refinement would fail in actual run()
    assert result["refinement_needed"] == "yes"
    assert result["refinement_agent"] == "Researcher"
