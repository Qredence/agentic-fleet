import asyncio
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

import dspy
from dspy.clients.base_lm import BaseLM
from agent_framework import AgentRunEvent

from agentic_fleet.workflows.modules import build_modules_workflow


class RoutingLM(BaseLM):
    def __init__(self, pattern: str, target_team: str = "default"):
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


async def run_case(pattern: str) -> list[str]:
    os.environ["FLEET_MODEL_ROUTING"] = "0"
    dspy.settings.configure(lm=RoutingLM(pattern))
    workflow = build_modules_workflow()
    result = await workflow.run("Hello")
    return [event.executor_id for event in result if isinstance(event, AgentRunEvent)]


async def main():
    complex_trace = await run_case("complex")
    assert "Router" in complex_trace, f"Router missing: {complex_trace}"
    assert "Planner" in complex_trace, f"Planner missing: {complex_trace}"
    assert "Worker" in complex_trace, f"Worker missing: {complex_trace}"
    assert "Judge" in complex_trace, f"Judge missing: {complex_trace}"

    simple_trace = await run_case("simple")
    assert "Router" in simple_trace, f"Router missing: {simple_trace}"
    assert "Worker" in simple_trace, f"Worker missing: {simple_trace}"
    assert "Planner" not in simple_trace, f"Planner should be skipped: {simple_trace}"
    assert "Judge" not in simple_trace, f"Judge should be skipped: {simple_trace}"

    print("Phase 3 verification passed.")


if __name__ == "__main__":
    asyncio.run(main())
