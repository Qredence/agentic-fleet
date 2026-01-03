import asyncio
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

import dspy
from dspy.clients.base_lm import BaseLM

from agentic_fleet.agents.base import BaseFleetAgent
from agentic_fleet.dspy_modules.signatures import PlannerSignature, TaskContext
from agentic_fleet.gepa.optimizer import FleetOptimizer


class DummyLM(BaseLM):
    def __init__(self):
        super().__init__(model="dummy", model_type="chat", cache=False)

    def forward(self, prompt=None, messages=None, **kwargs):
        payload = {
            "reasoning": "ok",
            "plan": "step one",
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


async def main() -> None:
    os.environ["FLEET_MODEL_ROUTING"] = "0"
    dspy.settings.configure(lm=DummyLM())
    state_dir = ".context/state"

    training_data = [
        dspy.Example(
            task="Task A",
            context=TaskContext(team_id="default", constraints=[], tools=[]),
            plan="Plan A",
            result="Result A",
        ).with_inputs("task", "context"),
        dspy.Example(
            task="Task B",
            context=TaskContext(team_id="default", constraints=[], tools=[]),
            plan="Plan B",
            result="Result B",
        ).with_inputs("task", "context"),
        dspy.Example(
            task="Task C",
            context=TaskContext(team_id="default", constraints=[], tools=[]),
            plan="Plan C",
            result="Result C",
        ).with_inputs("task", "context"),
    ]

    optimizer = FleetOptimizer()
    output_path = optimizer.compile(
        training_data,
        output_path=state_dir,
    )

    assert output_path.exists(), f"Expected {output_path} to exist."

    agent = BaseFleetAgent(
        name="Planner",
        role="architect",
        brain_signature=PlannerSignature,
        brain_state_path=str(output_path),
    )

    response = await agent.run("Hello")
    assert response.text, "Expected a response from the agent."

    print("Phase 5 verification passed.")


if __name__ == "__main__":
    asyncio.run(main())
