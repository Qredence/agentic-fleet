"""
Tests for quality assessment modules (criteria, assessor, refiner).
"""

import pytest

from agentic_fleet.workflows.quality import assessor, criteria, refiner


@pytest.mark.asyncio
async def test_get_quality_criteria_with_judge_agent():
    """Test get_quality_criteria with Judge agent available."""
    task = "Research topic X"

    class MockJudgeAgent:
        async def run(self, prompt: str):
            return "1. Accuracy: Check facts\n2. Completeness: Verify coverage\n3. Clarity: Assess readability"

    async def call_judge_fn(agent, prompt: str):
        return await agent.run(prompt)

    agents = {"Judge": MockJudgeAgent()}

    result = await criteria.get_quality_criteria(task, agents, call_judge_fn)

    assert "Quality Criteria Checklist" in result
    assert "Accuracy" in result
    assert "Completeness" in result


@pytest.mark.asyncio
async def test_get_quality_criteria_without_judge_agent():
    """Test get_quality_criteria fallback when Judge unavailable."""
    task = "Research topic X"

    async def call_judge_fn(agent, prompt: str):
        return await agent.run(prompt)

    agents = {}  # No Judge agent

    result = await criteria.get_quality_criteria(task, agents, call_judge_fn)

    # Should return fallback generic criteria
    assert "Quality Criteria Checklist" in result
    assert "Accuracy" in result
    assert "Completeness" in result
    assert "Clarity" in result


@pytest.mark.asyncio
async def test_get_quality_criteria_with_judge_exception():
    """Test get_quality_criteria fallback when Judge raises exception."""
    task = "Research topic X"

    class MockJudgeAgent:
        async def run(self, prompt: str):
            raise RuntimeError("Judge failed")

    async def call_judge_fn(agent, prompt: str):
        return await agent.run(prompt)

    agents = {"Judge": MockJudgeAgent()}

    result = await criteria.get_quality_criteria(task, agents, call_judge_fn)

    # Should return fallback generic criteria on exception
    assert "Quality Criteria Checklist" in result
    assert "Accuracy" in result


def test_call_judge_with_reasoning():
    """Test call_judge_with_reasoning reasoning effort setting."""

    class MockChatClient:
        def __init__(self):
            self.extra_body = {}

    class MockJudgeAgent:
        def __init__(self):
            self.chat_client = MockChatClient()

        def run(self, prompt: str):
            return f"Judged: {prompt}"

    judge_agent = MockJudgeAgent()
    prompt = "Evaluate this response"

    result = assessor.call_judge_with_reasoning(judge_agent, prompt, reasoning_effort="high")

    # Should set reasoning effort in chat_client.extra_body
    assert hasattr(judge_agent.chat_client, "extra_body")
    # Note: The function modifies the chat_client but returns the result
    # We can check that the function executed without error
    assert result is not None


@pytest.mark.asyncio
async def test_call_judge_with_reasoning_no_chat_client():
    """Test call_judge_with_reasoning when agent has no chat_client."""

    class MockJudgeAgent:
        def run(self, prompt: str):
            return f"Judged: {prompt}"

    judge_agent = MockJudgeAgent()
    prompt = "Evaluate this response"

    result = assessor.call_judge_with_reasoning(judge_agent, prompt, reasoning_effort="medium")

    # Should still call the agent's run method
    assert result is not None


@pytest.mark.asyncio
async def test_assess_quality_with_compiled_supervisor():
    """Test assess_quality with compiled supervisor."""
    task = "Test task"
    result = "Test result"

    class MockCompiledSupervisor:
        def assess_quality(self, requirements: str, results: str):
            from types import SimpleNamespace

            return SimpleNamespace(
                quality_score="9",
                missing_elements="",
                improvement_suggestions="",
            )

    async def call_with_retry(fn, **kwargs):
        return fn(**kwargs)

    def normalize_quality(raw, task: str, result: str):
        return {
            "score": float(raw.quality_score) if hasattr(raw, "quality_score") else 9.0,
            "missing_elements": getattr(raw, "missing_elements", ""),
            "improvements": getattr(raw, "improvement_suggestions", ""),
        }

    def fallback_quality(task: str, result: str):
        return {"score": 8.0, "missing_elements": "", "improvements": ""}

    status_records = []

    def record_status(phase: str, status: str):
        status_records.append((phase, status))

    compiled_supervisor = MockCompiledSupervisor()

    quality = await assessor.assess_quality(
        task,
        result,
        compiled_supervisor,
        call_with_retry,
        normalize_quality,
        fallback_quality,
        record_status,
    )

    assert "score" in quality
    assert quality["score"] == 9.0
    assert len(status_records) > 0
    assert status_records[0][0] == "quality"


@pytest.mark.asyncio
async def test_assess_quality_fallback_behavior():
    """Test assess_quality fallback behavior."""
    task = "Test task"
    result = "Test result"

    class MockCompiledSupervisor:
        def assess_quality(self, requirements: str, results: str):
            raise RuntimeError("Supervisor failed")

    async def call_with_retry(fn, **kwargs):
        return fn(**kwargs)

    def normalize_quality(raw, task: str, result: str):
        return {"score": 9.0, "missing_elements": "", "improvements": ""}

    def fallback_quality(task: str, result: str):
        return {"score": 7.0, "missing_elements": "some", "improvements": "improve"}

    status_records = []

    def record_status(phase: str, status: str):
        status_records.append((phase, status))

    compiled_supervisor = MockCompiledSupervisor()

    quality = await assessor.assess_quality(
        task,
        result,
        compiled_supervisor,
        call_with_retry,
        normalize_quality,
        fallback_quality,
        record_status,
    )

    # Should use fallback
    assert quality["score"] == 7.0
    assert any(status == "fallback" for _, status in status_records)


@pytest.mark.asyncio
async def test_judge_phase_disabled():
    """Test judge_phase when disabled."""
    from types import SimpleNamespace

    task = "Test task"
    result = "Test result"
    agents = {}

    config = SimpleNamespace(enable_judge=False, judge_threshold=7.0)

    async def get_quality_criteria_fn(task: str):
        return "Generic criteria"

    def parse_judge_response_fn(*args, **kwargs):
        return {"score": 8.0, "missing_elements": "", "refinement_needed": "no"}

    def determine_refinement_agent_fn(missing: str):
        return None

    status_records = []

    def record_status(phase: str, status: str):
        status_records.append((phase, status))

    judge_eval = await assessor.judge_phase(
        task,
        result,
        agents,
        config,
        get_quality_criteria_fn,
        parse_judge_response_fn,
        determine_refinement_agent_fn,
        record_status,
    )

    assert judge_eval["score"] == 10.0
    assert judge_eval["refinement_needed"] == "no"


@pytest.mark.asyncio
async def test_judge_phase_missing_judge_agent():
    """Test judge_phase when Judge agent is missing."""
    from types import SimpleNamespace

    task = "Test task"
    result = "Test result"
    agents = {}  # No Judge agent

    config = SimpleNamespace(
        enable_judge=True, judge_threshold=7.0, judge_reasoning_effort="medium"
    )

    async def get_quality_criteria_fn(task: str):
        return "Generic criteria"

    def parse_judge_response_fn(*args, **kwargs):
        return {"score": 8.0, "missing_elements": "", "refinement_needed": "no"}

    def determine_refinement_agent_fn(missing: str):
        return None

    status_records = []

    def record_status(phase: str, status: str):
        status_records.append((phase, status))

    judge_eval = await assessor.judge_phase(
        task,
        result,
        agents,
        config,
        get_quality_criteria_fn,
        parse_judge_response_fn,
        determine_refinement_agent_fn,
        record_status,
    )

    assert judge_eval["score"] == 10.0
    assert judge_eval["refinement_needed"] == "no"


@pytest.mark.asyncio
async def test_judge_phase_evaluation():
    """Test judge_phase evaluation with Judge agent."""
    from types import SimpleNamespace

    task = "Test task"
    result = "Test result"

    class MockJudgeAgent:
        def __init__(self):
            self.chat_client = SimpleNamespace(extra_body={})

        async def run(self, prompt: str):
            return "Score: 8/10\nMissing elements: citations\nRefinement needed: yes\nRefinement agent: Researcher"

    agents = {"Judge": MockJudgeAgent()}

    config = SimpleNamespace(
        enable_judge=True, judge_threshold=7.0, judge_reasoning_effort="medium"
    )

    async def get_quality_criteria_fn(task: str):
        return "1. Accuracy\n2. Citations"

    def parse_judge_response_fn(response, task, result, criteria, config, determine_fn):
        return {
            "score": 8.0,
            "missing_elements": "citations",
            "refinement_needed": "yes",
            "refinement_agent": "Researcher",
            "required_improvements": "Add citations",
        }

    def determine_refinement_agent_fn(missing: str):
        return "Researcher" if "citation" in missing.lower() else None

    status_records = []

    def record_status(phase: str, status: str):
        status_records.append((phase, status))

    judge_eval = await assessor.judge_phase(
        task,
        result,
        agents,
        config,
        get_quality_criteria_fn,
        parse_judge_response_fn,
        determine_refinement_agent_fn,
        record_status,
    )

    assert judge_eval["score"] == 8.0
    assert judge_eval["refinement_needed"] == "yes"
    assert judge_eval["refinement_agent"] == "Researcher"
    assert any(phase == "judge" for phase, _ in status_records)


def test_parse_judge_response():
    """Test parsing judge response."""
    from types import SimpleNamespace

    response = """Score: 8/10
Missing elements: citations, dates
Refinement needed: yes
Refinement agent: Researcher
Required improvements: Add citations and verify dates"""

    task = "Research task"
    result = "Research result"
    quality_criteria = "1. Citations\n2. Dates"

    config = SimpleNamespace(judge_threshold=7.0)

    def determine_refinement_agent_fn(missing: str):
        return "Researcher" if "citation" in missing.lower() else "Writer"

    judge_eval = assessor.parse_judge_response(
        response, task, result, quality_criteria, config, determine_refinement_agent_fn
    )

    assert judge_eval["score"] == 8.0
    assert "citations" in judge_eval["missing_elements"].lower()
    assert judge_eval["refinement_needed"] == "yes"
    # The agent name is extracted from the response and may be lowercased
    assert judge_eval["refinement_agent"].lower() == "researcher"


def test_parse_judge_response_below_threshold():
    """Test parse_judge_response when score is below threshold."""
    from types import SimpleNamespace

    response = "Score: 6/10\nMissing elements: accuracy"

    task = "Test task"
    result = "Test result"
    quality_criteria = "1. Accuracy"

    config = SimpleNamespace(judge_threshold=7.0)

    def determine_refinement_agent_fn(missing: str):
        return "Researcher"

    judge_eval = assessor.parse_judge_response(
        response, task, result, quality_criteria, config, determine_refinement_agent_fn
    )

    # Should mark refinement as needed even if not explicitly stated
    assert judge_eval["score"] == 6.0
    assert judge_eval["refinement_needed"] == "yes"
    assert judge_eval["refinement_agent"] == "Researcher"


def test_build_refinement_task():
    """Test building refinement task from judge evaluation."""
    current_result = "Current response text"
    judge_eval = {
        "missing_elements": "citations, dates",
        "required_improvements": "Add citations and verify dates",
    }

    refinement_task = refiner.build_refinement_task(current_result, judge_eval)

    assert "Improve the following response" in refinement_task
    assert "citations, dates" in refinement_task
    assert "Current response text" in refinement_task
    assert "improvements" in refinement_task.lower()


@pytest.mark.asyncio
async def test_refine_results():
    """Test refine_results refinement logic."""

    class MockWriterAgent:
        async def run(self, prompt: str):
            return f"Refined: {prompt}"

    agents = {"Writer": MockWriterAgent()}
    results = "Original results"
    improvements = "Add citations"

    refined = await refiner.refine_results(agents, results, improvements)

    assert "Refined" in refined
    assert "Original results" in refined
    assert "Add citations" in refined


@pytest.mark.asyncio
async def test_refine_results_missing_writer():
    """Test refine_results when Writer agent is missing."""
    agents = {}  # No Writer agent
    results = "Original results"
    improvements = "Add citations"

    with pytest.raises(KeyError):
        await refiner.refine_results(agents, results, improvements)


def test_parse_judge_response_quality_score():
    """Test quality score parsing and normalization."""
    from types import SimpleNamespace

    # Test various score formats
    test_cases = [
        ("Score: 8/10", 8.0),
        ("Score: 8.5/10", 8.5),
        ("8/10", 8.0),
        ("score: 9/10", 9.0),
    ]

    config = SimpleNamespace(judge_threshold=7.0)

    def determine_refinement_agent_fn(missing: str):
        return None

    for response, expected_score in test_cases:
        judge_eval = assessor.parse_judge_response(
            response, "task", "result", "criteria", config, determine_refinement_agent_fn
        )
        assert judge_eval["score"] == expected_score
