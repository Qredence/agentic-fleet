import asyncio
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

import dspy
from dspy.clients.base_lm import BaseLM

from agentic_fleet import config
from agentic_fleet.agents.base import BaseFleetAgent
from agentic_fleet.middleware.context import ContextModulator
from agentic_fleet.dspy_modules.signatures import TaskContext


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


class TestSignature(dspy.Signature):
    task: str = dspy.InputField()
    context: TaskContext = dspy.InputField()
    plan: str = dspy.OutputField()


async def main():
    os.environ["FLEET_MODEL_ROUTING"] = "0"
    config.TEAM_REGISTRY.clear()
    config.TEAM_REGISTRY.update(
        {
            "research": {
                "tools": ["browser"],
                "credentials": {},
                "description": "research team",
            },
            "default": {
                "tools": [],
                "credentials": {},
                "description": "default team",
            },
        }
    )

    dummy_lm = DummyLM()
    dspy.settings.configure(lm=dummy_lm)

    agent = BaseFleetAgent(name="test-agent", role="tester", brain_signature=TestSignature)

    async with ContextModulator.scope("research"):
        await agent.run("Hello")

    combined = f"{dummy_lm.last_prompt}{dummy_lm.last_messages}"
    assert "research" in combined, f"Expected 'research' in prompt/messages, got: {combined}"

    print("Phase 2 verification passed.")


if __name__ == "__main__":
    asyncio.run(main())
