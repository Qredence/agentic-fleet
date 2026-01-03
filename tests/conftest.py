"""Pytest configuration and fixtures for agentic-fleet tests."""

import asyncio
import json
import sys
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock

import pytest
from agent_framework import ChatMessage, Role

# Add src to path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))


@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def dummy_lm():
    """Create a mock DSPy language model for testing."""
    from dspy.clients.base_lm import BaseLM

    class DummyLM(BaseLM):
        def __init__(self):
            super().__init__(model="dummy", model_type="chat")
            self.last_prompt = None
            self.last_messages = None

        def forward(self, prompt=None, messages=None, **kwargs):
            self.last_prompt = prompt
            self.last_messages = messages

            class Message:
                def __init__(self, content):
                    self.content = content

            class Choice:
                def __init__(self, content):
                    self.message = Message(content)

            class Response:
                def __init__(self, content):
                    self.choices = [Choice(content)]
                    self.usage = {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}
                    self.model = "dummy"

            return Response("ok")

    return DummyLM()


@pytest.fixture
def routing_lm():
    """Create a mock DSPy LM that returns routing decisions."""
    from dspy.clients.base_lm import BaseLM

    class RoutingLM(BaseLM):
        def __init__(self, pattern: str = "complex", target_team: str = "default"):
            super().__init__(model="dummy", model_type="chat", cache=False)
            self.pattern = pattern
            self.target_team = target_team

        def forward(self, prompt=None, messages=None, **kwargs):
            payload = {
                "reasoning": "test routing",
                "decision": {
                    "pattern": self.pattern,
                    "target_team": self.target_team,
                    "reasoning": "because",
                },
            }
            content = json.dumps(payload)

            class Message:
                def __init__(self, content):
                    self.content = content

            class Choice:
                def __init__(self, content):
                    self.message = Message(content)

            class Response:
                def __init__(self, content):
                    self.choices = [Choice(content)]
                    self.usage = {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}
                    self.model = "dummy"

            return Response(content)

    return RoutingLM


@pytest.fixture
def sample_task_context():
    """Create a sample TaskContext for testing."""
    from agentic_fleet.dspy_modules.signatures import TaskContext

    return TaskContext(
        team_id="research",
        constraints=["deep research"],
        tools=["browser", "search"],
    )


@pytest.fixture
def temp_state_dir(tmp_path):
    """Create a temporary directory for state files."""
    state_dir = tmp_path / "state"
    state_dir.mkdir()
    return state_dir


@pytest.fixture
def chat_message():
    """Create a sample ChatMessage."""
    return ChatMessage(role=Role.USER, text="Hello, test!")


@pytest.fixture
def reset_team_registry():
    """Reset TEAM_REGISTRY before and after each test."""
    from agentic_fleet import config

    # Backup original registry
    original_registry = config.TEAM_REGISTRY.copy()

    # Clear and set test registry
    config.TEAM_REGISTRY.clear()
    config.TEAM_REGISTRY.update(
        {
            "research": {
                "tools": ["browser", "search", "synthesize"],
                "credentials": {},
                "description": "research team",
            },
            "coding": {
                "tools": ["repo_read", "repo_write", "tests"],
                "credentials": {},
                "description": "coding team",
            },
            "default": {
                "tools": ["general"],
                "credentials": {},
                "description": "default team",
            },
        }
    )

    yield

    # Restore original registry
    config.TEAM_REGISTRY.clear()
    config.TEAM_REGISTRY.update(original_registry)
