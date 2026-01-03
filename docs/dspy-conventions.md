# DSPy Conventions Guide

This document covers DSPy patterns, conventions, and best practices used in Agentic Fleet v2.0, based on official DSPy documentation from Context7.

## Table of Contents

1. [Signatures](#signatures)
2. [Modules](#modules)
3. [Chain of Thought](#chain-of-thought)
4. [Training Examples](#training-examples)
5. [Optimizers](#optimizers)
6. [Saving and Loading](#saving-and-loading)
7. [Best Practices](#best-practices)

---

## Signatures

Signatures are the core of DSPy. They define the input and output structure for LLM calls.

### Basic Signature Definition

```python
import dspy

class BasicQA(dspy.Signature):
    """Answer the question based on the context."""
    question: str = dspy.InputField(desc="the question to answer")
    context: str = dspy.InputField(desc="relevant context")
    answer: str = dspy.OutputField(desc="the answer to the question")
```

### InputField and OutputField

```python
class MySignature(dspy.Signature):
    # Required input with description
    input_field: str = dspy.InputField(
        desc="description of the input for the LLM"
    )

    # Optional input with default
    optional_input: str = dspy.InputField(
        desc="optional input",
        default=""
    )

    # Output with format constraint
    output_field: str = dspy.OutputField(
        desc="description of the output",
        prefix="Answer: "  # Optional prefix in prompt
    )

    # Typed output
    confidence: float = dspy.OutputField(
        desc="confidence score between 0 and 1",
        format=lambda x: float(x) if x else 0.5
    )
```

### Agentic Fleet Signature Examples

```python
# Router Signature - routes tasks to teams/patterns
class RouterSignature(dspy.Signature):
    """Route the given task to the appropriate team and pattern."""
    task: str = dspy.InputField(desc="the user's task description")
    decision: RoutingDecision = dspy.OutputField(desc="routing decision with pattern and team")

# Planner Signature - creates execution plans
class PlannerSignature(dspy.Signature):
    """Create a step-by-step execution plan for the given task."""
    task: str = dspy.InputField(desc="the task to plan")
    context: TaskContext = dspy.InputField(desc="team context with constraints")
    plan: str = dspy.OutputField(desc="numbered step-by-step plan")
    reasoning: str = dspy.OutputField(desc="reasoning for the plan approach")

# Worker Signature - executes plan steps
class WorkerSignature(dspy.Signature):
    """Execute the given step and report the result."""
    step: str = dspy.InputField(desc="the step to execute")
    context: TaskContext = dspy.InputField(desc="team context")
    action: str = dspy.OutputField(desc="action taken")
    result: ExecutionResult = dspy.OutputField(desc="execution result")

# Judge Signature - reviews output quality
class JudgeSignature(dspy.Signature):
    """Review the result and determine if it meets quality standards."""
    original_task: str = dspy.InputField(desc="original user task")
    result: ExecutionResult = dspy.InputField(desc="result to review")
    is_approved: bool = dspy.OutputField(desc="true if approved, false if needs revision")
    critique: str = dspy.OutputField(desc="feedback if not approved")
```

---

## Modules

Modules are DSPy's building blocks for composing LLM programs.

### Creating Custom Modules

```python
import dspy

class MyModule(dspy.Module):
    """Custom module wrapping DSPy components."""

    def __init__(self):
        super().__init__()
        # Initialize sub-modules
        self.generator = dspy.ChainOfThought(MySignature)
        self.evaluator = dspy.ChainOfThought(EvalSignature)

    def forward(self, input_text: str) -> dict:
        """Forward pass through the module."""
        # Call sub-modules
        result = self.generator(input_field=input_text)
        evaluation = self.evaluator(result=result.output_field)

        return {
            "generated": result.output_field,
            "evaluation": evaluation.is_valid,
        }
```

### FleetBrain - Agentic Fleet's Custom Module

```python
class FleetBrain(dspy.Module):
    """Wrapper that injects active team context into DSPy calls."""

    def __init__(self, signature: type[dspy.Signature], brain_state_path: str | None = None):
        super().__init__()
        self.signature = signature
        self.brain_state_path = brain_state_path
        # Initialize ChainOfThought with the signature
        self.program = dspy.ChainOfThought(signature)
        # Load compiled state if available
        if brain_state_path:
            self.program.load(brain_state_path)

    def forward(self, **kwargs: Any) -> Any:
        """Inject context if not provided, then call DSPy program."""
        # Context injection pattern
        if "context" in self.signature.input_fields and "context" not in kwargs:
            ctx = ContextModulator.get_current()
            if ctx is not None:
                kwargs["context"] = TaskContext(**ctx)

        return self.program(**kwargs)
```

---

## Chain of Thought

ChainOfThought is DSPy's built-in module that adds reasoning to any signature.

### Basic Usage

```python
import dspy

# Define signature
class MathProblem(dspy.Signature):
    """Solve the math problem step by step."""
    problem: str = dspy.InputField(desc="the math problem")
    solution: str = dspy.OutputField(desc="step-by-step solution")

# Create ChainOfThought module
cot_module = dspy.ChainOfThought(MathProblem)

# Execute
result = cot_module(problem="What is 15% of 80?")
print(result.solution)  # Includes reasoning
```

### Customizing ChainOfThought

```python
# With explicit reasoning field
class MathProblemWithReasoning(dspy.Signature):
    """Solve the math problem with clear reasoning."""
    problem: str = dspy.InputField(desc="the math problem")
    reasoning: str = dspy.OutputField(desc="step-by-step reasoning")
    solution: str = dspy.OutputField(desc="final answer")

cot = dspy.ChainOfThought(MathProblemWithReasoning)
```

### Using with Multiple Inputs

```python
class QASignature(dspy.Signature):
    """Answer question based on context."""
    question: str = dspy.InputField()
    context: str = dspy.InputField()
    answer: str = dspy.OutputField()

qa = dspy.ChainOfThought(QASignature)

# Can pass as dict or kwargs
result = qa(question="What is X?", context="X is Y")
# or
result = qa({"question": "What is X?", "context": "X is Y"})
```

---

## Training Examples

Training examples are the foundation of DSPy optimization.

### Creating Examples

```python
import dspy

# Basic example
example = dspy.Example(
    question="What is the capital of France?",
    answer="Paris"
)

# With multiple fields
example = dspy.Example(
    task="Research AI trends",
    context=TaskContext(team_id="research", constraints=[], tools=[]),
    plan="1. Search for recent AI trends\n2. Synthesize findings",
    result="AI trends report"
).with_inputs("task", "context")
```

### Specifying Input Fields

```python
# Mark which fields are inputs (others are outputs)
example = dspy.Example(
    task="Analyze data",
    plan="1. Load data\n2. Clean data\n3. Analyze",
    result="Analysis complete"
).with_inputs("task")  # Only 'task' is input

# Multiple input fields
example = dspy.Example(
    task="Summarize",
    context="Long text...",
    summary="Short summary",
    word_count=50
).with_inputs("task", "context")
```

### Dataset Example

```python
# Training dataset for router
training_data = [
    dspy.Example(
        task="What is the weather in Tokyo?",
        context=TaskContext(team_id="default", constraints=[], tools=[]),
        decision=RoutingDecision(
            pattern="simple",
            target_team="default",
            reasoning="Simple question about weather"
        )
    ).with_inputs("task", "context"),

    dspy.Example(
        task="Research quantum computing advances in 2024",
        context=TaskContext(team_id="research", constraints=["deep research"], tools=["browser"]),
        decision=RoutingDecision(
            pattern="complex",
            target_team="research",
            reasoning="Requires deep research and synthesis"
        )
    ).with_inputs("task", "context"),
]

# Training dataset for planner
planner_training = [
    dspy.Example(
        task="Create a Python web scraper",
        context=TaskContext(team_id="coding", constraints=["follow PEP 8"], tools=["repo_read"]),
        plan="1. Design scraper architecture\n2. Implement parsing\n3. Add error handling\n4. Write tests",
        result="Completed scraper with tests"
    ).with_inputs("task", "context"),
]
```

---

## Optimizers

DSPy optimizers automatically improve prompts and weights for your programs.

### BootstrapFewShot

The most commonly used optimizer for few-shot learning:

```python
import dspy
from dspy.teleprompt import BootstrapFewShot

# Configure language model
dspy.configure(lm=dspy.LM("openai/gpt-4o-mini"))

# Create base program
program = dspy.ChainOfThought(RouterSignature)

# Define metric function
def router_metric(example: dspy.Example, prediction, **kwargs) -> bool:
    """Check if router predicted correct pattern."""
    predicted_pattern = prediction.decision.pattern
    expected_pattern = example.decision.pattern
    return predicted_pattern == expected_pattern

# Create optimizer
optimizer = BootstrapFewShot(
    metric=router_metric,
    max_bootstrapped_demos=4,      # Max demos to generate
    max_labeled_demos=16,          # Max labeled demos to use
    max_rounds=1,                  # Number of optimization rounds
    max_errors=10,                 # Max errors before stopping
)

# Compile program
compiled_program = optimizer.compile(
    student=program,
    trainset=training_data,
    teacher=program,  # Optional teacher program
)
```

### Available Optimizers

```python
# BootstrapFewShot - Simple few-shot from demonstrations
from dspy.teleprompt import BootstrapFewShot

# COPE - Optimizes with critique
from dspy.teleprompt import COPE

# BayesianSearch - Grid search over hyperparameters
from dspy.teleprompt import BayesianSearch

# KNNFewShot - K-nearest neighbors for demonstrations
from dspy.teleprompt import KNNFewShot
```

### Custom Metric

```python
def custom_metric(example, prediction, **kwargs) -> float:
    """
    Return score between 0 and 1.
    DSPy maximizes this score.
    """
    # Example: Exact match
    return 1.0 if prediction.answer == example.answer else 0.0

# Or with partial credit
def graded_metric(example, prediction, **kwargs) -> float:
    """Return score based on partial correctness."""
    predicted = prediction.answer.lower().strip()
    expected = example.answer.lower().strip()

    if predicted == expected:
        return 1.0
    elif predicted in expected or expected in predicted:
        return 0.5
    return 0.0
```

---

## Saving and Loading

Compiled programs can be saved and loaded for reuse.

### Saving a Program

```python
# Save compiled program
compiled_program.save(
    "./state/planner_opt.json",
    save_program=True,
    modules_to_serialize=[custom_module]  # Include custom modules
)
```

### Loading a Program

```python
# Load compiled program
program = dspy.ChainOfThought(PlannerSignature)
program.load("./state/planner_opt.json")
```

### FleetOptimizer Implementation

```python
from pathlib import Path
import dspy
from dspy.teleprompt import BootstrapFewShot

class FleetOptimizer:
    """Compiles DSPy programs using GEPA methodology."""

    def __init__(self, output_dir: str = "dspy_modules/state"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def compile(
        self,
        program: dspy.Module,
        training_data: list[dspy.Example],
        output_path: str | None = None,
    ) -> dspy.Module:
        """Compile the program using BootstrapFewShot."""
        optimizer = BootstrapFewShot(
            metric=self._default_metric,
            max_bootstrapped_demos=4,
            max_labeled_demos=16,
        )

        compiled = optimizer.compile(program, trainset=training_data)

        # Save compiled state
        save_path = output_path or str(self.output_dir / "planner_opt.json")
        compiled.save(save_path)

        return compiled

    def _default_metric(self, example: dspy.Example, prediction: Any, **kwargs) -> bool:
        """Default metric for optimization."""
        return kwargs.get("is_approved", False)
```

---

## Best Practices

### 1. Signature Design

```python
# ✅ Good: Clear, specific descriptions
class GoodSignature(dspy.Signature):
    """Extract entity names from the given text."""
    text: str = dspy.InputField(desc="text containing entity names")
    entities: list[str] = dspy.OutputField(desc="list of entity names found")

# ❌ Bad: Vague descriptions
class BadSignature(dspy.Signature):
    text: str = dspy.InputField()
    entities: list[str] = dspy.OutputField()
```

### 2. Field Descriptions

```python
# ✅ Good: Descriptive and informative
class QA(dspy.Signature):
    question: str = dspy.InputField(
        desc="the user's question, including any relevant context"
    )
    answer: str = dspy.OutputField(
        desc="concise answer to the question, max 2 sentences"
    )

# ❌ Bad: Unhelpful descriptions
class QA(dspy.Signature):
    question: str = dspy.InputField(desc="question")
    answer: str = dspy.OutputField(desc="answer")
```

### 3. Type Annotations

```python
from typing import Optional

class TaskSignature(dspy.Signature):
    # Required field
    task: str = dspy.InputField(desc="the task description")

    # Optional field with default
    context: Optional[str] = dspy.InputField(
        desc="optional context",
        default=None
    )

    # Structured output
    result: dict = dspy.OutputField(desc="structured result as JSON")
```

### 4. Context Injection

```python
class ContextAwareSignature(dspy.Signature):
    """Task execution with team context."""
    task: str = dspy.InputField(desc="task to execute")
    context: TaskContext = dspy.InputField(desc="team context")
    result: str = dspy.OutputField(desc="execution result")

class FleetBrain(dspy.Module):
    def forward(self, **kwargs):
        # Auto-inject context if not provided
        if "context" not in kwargs:
            ctx = ContextModulator.get_current()
            if ctx is not None:
                kwargs["context"] = TaskContext(**ctx)
        return self.program(**kwargs)
```

### 5. Error Handling

```python
def safe_execute(program: dspy.Module, **inputs) -> Any:
    """Execute program with error handling."""
    try:
        return program(**inputs)
    except Exception as e:
        # Log error
        print(f"Error executing program: {e}")
        # Return fallback
        return None
```

### 6. Evaluation Setup

```python
# Split data for evaluation
from sklearn.model_selection import train_test_split

train_data, eval_data = train_test_split(
    all_examples,
    test_size=0.2,
    random_state=42
)

# Optimize on training data
optimizer.compile(program, trainset=train_data)

# Evaluate on held-out data
total_score = 0
for example in eval_data:
    prediction = program(**example.inputs())
    score = metric(example, prediction)
    total_score += score

avg_score = total_score / len(eval_data)
print(f"Average score: {avg_score:.2f}")
```

---

## Summary

| Pattern | DSPy Convention | Agentic Fleet Usage |
|---------|-----------------|---------------------|
| Signature | `class X(dspy.Signature)` | `RouterSignature`, `PlannerSignature` |
| InputField | `field: type = dspy.InputField(desc="...")` | Task input, context |
| OutputField | `field: type = dspy.OutputField(desc="...")` | Decision, plan, result |
| ChainOfThought | `dspy.ChainOfThought(Signature)` | Brain computation |
| Training Example | `dspy.Example(...).with_inputs(...)` | GEPA training data |
| Optimization | `BootstrapFewShot.compile()` | FleetOptimizer |
| Saving | `program.save(path)` | `planner_opt.json` |
