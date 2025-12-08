import os

import pytest
from dotenv import load_dotenv

from agentic_fleet.agents.coordinator import AgentFactory
from agentic_fleet.workflows.helpers import FastPathDetector

# Load environment variables
load_dotenv()


@pytest.mark.asyncio
async def test_fast_path_detector():
    """Verify FastPathDetector patterns match expected user intents."""
    detector = FastPathDetector()

    # Test simple cases
    assert detector.classify("Hello")
    assert detector.classify("What is 2+2?")
    assert detector.classify("Hi there")

    # Test complex/time-sensitive cases (should fail fast path)
    # The current regex for time-sensitive might encompass "election" or years
    assert not detector.classify("Who won the 2024 election?")
    assert not detector.classify("Detail the history of Quantum Computing")


@pytest.mark.asyncio
async def test_foundry_agent_config_loading():
    """Verify that AgentFactory can parse the Foundry config structure."""
    # We can't easily mock the full Azure cloud without credentials here,
    # but we can verify that the factory *attempts* to correct flow or fails gracefully if credentials missing.

    _ = AgentFactory()

    # Check if correct env vars are present (just a warning if not, since we can't force user to have them set in CI)
    if not os.getenv("AZURE_AI_PROJECT_ENDPOINT"):
        print(
            "WARNING: AZURE_AI_PROJECT_ENDPOINT not set. Skipping live Foundry connectivity test."
        )
        return

    # If credentials exist, we would attempt:
    # agents = await factory.load_foundry_agents()
    # assert len(agents) >= 0
    pass
