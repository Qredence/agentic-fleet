from unittest.mock import MagicMock

from agentic_fleet.dspy_modules.reasoner_utils import is_time_sensitive_task
from agentic_fleet.workflows.helpers import FastPathDetector
from agentic_fleet.workflows.narrator import EventNarrator, WorkflowEvent

# --- FastPathDetector Tests ---


def test_fast_path_detector_simple():
    detector = FastPathDetector()
    assert detector.classify("hi") is True
    assert detector.classify("hello there") is True
    assert detector.classify("what is python") is True


def test_fast_path_detector_complex():
    detector = FastPathDetector()
    assert detector.classify("write a comprehensive report on AI") is False
    assert detector.classify("plan a comprehensive marketing strategy") is False
    assert detector.classify("analyze the stock market") is False


def test_fast_path_detector_time_sensitive():
    detector = FastPathDetector()
    assert detector.classify("who is the president in 2025") is False
    assert detector.classify("latest news today") is False


def test_fast_path_detector_length():
    detector = FastPathDetector(max_words=5)
    assert detector.classify("this is a very long task description that should fail") is False


# --- is_time_sensitive_task Tests ---


def test_is_time_sensitive_keywords():
    assert is_time_sensitive_task("what is the weather today") is True
    assert is_time_sensitive_task("latest news") is True
    assert (
        is_time_sensitive_task("who is creating python") is False
    )  # "creating" is not a time keyword


def test_is_time_sensitive_years():
    assert is_time_sensitive_task("events in 2023") is True
    assert is_time_sensitive_task("events in 2025") is True
    assert is_time_sensitive_task("history of 1999") is False


# --- EventNarrator Tests ---


def test_event_narrator_mock():
    # We mock dspy to avoid actual LLM calls
    narrator = EventNarrator()
    narrator.generate_narrative = MagicMock(return_value=MagicMock(narrative="Mock narrative"))

    events = [
        WorkflowEvent(timestamp="10:00", type="task", data={"action": "start task"}),
        WorkflowEvent(timestamp="10:01", type="completion", data={"status": "done"}),
    ]

    # We invoke forward directly or via call if mocked properly at class level
    # Since EventNarrator inherits dspy.Module, we can just call forward
    result = narrator.forward(events)
    assert result.narrative == "Mock narrative"
