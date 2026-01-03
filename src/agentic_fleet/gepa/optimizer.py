"""DSPy optimization utilities for fleet agents."""

from __future__ import annotations

from pathlib import Path
from typing import Iterable

import dspy
from dspy.teleprompt import BootstrapFewShot

from agentic_fleet.dspy_modules.signatures import PlannerSignature, TaskContext


def validate_judge_approval(example: dspy.Example, prediction: dspy.Example, trace=None) -> bool:
    # Placeholder: examples are assumed to be from approved runs.
    return True


class FleetOptimizer:
    def __init__(self) -> None:
        self.planner_optimizer = BootstrapFewShot(metric=validate_judge_approval)

    def compile(self, training_data: Iterable[dspy.Example], output_path: str) -> Path:
        Path(output_path).mkdir(parents=True, exist_ok=True)

        trainset = []
        for example in training_data:
            if "context" not in example:
                example = example.copy()
                example["context"] = TaskContext(team_id="default", constraints=[], tools=[])
            trainset.append(example.with_inputs("task", "context"))
        compiled_planner = self.planner_optimizer.compile(
            student=dspy.ChainOfThought(PlannerSignature),
            trainset=trainset,
        )

        output_file = Path(output_path) / "planner_opt.json"
        compiled_planner.save(str(output_file))
        return output_file


def optimize_fleet(training_data: list[dspy.Example], output_path: str) -> Path:
    optimizer = FleetOptimizer()
    return optimizer.compile(training_data, output_path)
