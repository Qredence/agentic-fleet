"""DSPy module logic for core roles."""

from __future__ import annotations

import dspy

from agentic_fleet.dspy_modules.signatures import (
    JudgeSignature,
    PlannerSignature,
    TaskContext,
    WorkerSignature,
)


class PlannerBrain(dspy.Module):
    def __init__(self) -> None:
        super().__init__()
        self.program = dspy.ChainOfThought(PlannerSignature)

    def forward(self, task: str, context: TaskContext):
        return self.program(task=task, context=context)


class WorkerBrain(dspy.Module):
    def __init__(self) -> None:
        super().__init__()
        self.program = dspy.ChainOfThought(WorkerSignature)

    def forward(self, step: str, context: TaskContext):
        return self.program(step=step, context=context)


class JudgeBrain(dspy.Module):
    def __init__(self) -> None:
        super().__init__()
        self.program = dspy.ChainOfThought(JudgeSignature)

    def forward(self, original_task: str, result):
        return self.program(original_task=original_task, result=result)
