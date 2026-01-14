"""DSPy signatures for agentic fleet.

This module defines the input/output signatures used by the DSPyReasoner
to perform cognitive tasks.

Refactored to enforce Pydantic-based typed signatures for all operations.

Includes handoff signatures (merged from handoff_signatures.py) for agent-to-agent
workflow handoffs.
"""

from __future__ import annotations

import dspy

from .typed_models import (
    ProgressEvaluationOutput,
    QualityAssessmentOutput,
    RoutingDecisionOutput,
    TaskAnalysisOutput,
    ToolPlanOutput,
    WorkflowStrategyOutput,
)


class TaskAnalysis(dspy.Signature):
    """Analyze a task with structured output.

    Returns a validated TaskAnalysisOutput with type-safe fields.
    """

    task: str = dspy.InputField(desc="The user's task description")
    analysis: TaskAnalysisOutput = dspy.OutputField(
        desc="Structured analysis of the task including complexity, capabilities, and tool needs"
    )


class TaskRouting(dspy.Signature):
    """Route a task to agents with structured output.

    CRITICAL: Assign the minimum necessary agents to complete the task efficiently.
    Do not over-assign. For simple tasks, a single agent is preferred.

    Returns a validated RoutingDecisionOutput with type-safe fields.
    """

    task: str = dspy.InputField(desc="The task to route")
    team: str = dspy.InputField(desc="Description of available agents")
    context: str = dspy.InputField(desc="Optional execution context")
    current_date: str = dspy.InputField(desc="Current date for time-sensitive decisions")

    decision: RoutingDecisionOutput = dspy.OutputField(
        desc="Structured routing decision with agents, mode, subtasks, and tools"
    )


class EnhancedTaskRouting(dspy.Signature):
    """Advanced task routing with structured output.

    Optimizes for latency and token usage by pre-planning tool usage
    and setting execution constraints.

    Returns a validated RoutingDecisionOutput with all routing fields.
    """

    task: str = dspy.InputField(desc="Task to be routed")
    team_capabilities: str = dspy.InputField(desc="Capabilities of available agents")
    available_tools: str = dspy.InputField(desc="List of available tools")
    current_context: str = dspy.InputField(desc="Execution context")
    handoff_history: str = dspy.InputField(desc="History of agent handoffs")
    workflow_state: str = dspy.InputField(desc="Current state of the workflow")

    decision: RoutingDecisionOutput = dspy.OutputField(
        desc="Complete routing decision with agents, mode, tools, and strategy"
    )


class QualityAssessment(dspy.Signature):
    """Assess result quality with structured output.

    Returns a validated QualityAssessmentOutput with score and feedback.
    """

    task: str = dspy.InputField(desc="The original task")
    result: str = dspy.InputField(desc="The result produced by the agent")

    assessment: QualityAssessmentOutput = dspy.OutputField(
        desc="Quality assessment with score (0-10), missing elements, and improvements"
    )


class ProgressEvaluation(dspy.Signature):
    """Evaluate progress with structured output.

    Returns a validated ProgressEvaluationOutput with action and feedback.
    """

    task: str = dspy.InputField(desc="The original task")
    result: str = dspy.InputField(desc="The current result")

    evaluation: ProgressEvaluationOutput = dspy.OutputField(
        desc="Progress evaluation with action (complete/refine/continue) and feedback"
    )


class ToolPlan(dspy.Signature):
    """Generate tool plan with structured output.

    Returns a validated ToolPlanOutput with ordered tool list.
    """

    task: str = dspy.InputField(desc="The task to execute")
    available_tools: str = dspy.InputField(desc="List of available tools")

    plan: ToolPlanOutput = dspy.OutputField(
        desc="Tool plan with ordered list of tools and reasoning"
    )


class WorkflowStrategy(dspy.Signature):
    """Select workflow strategy with structured output.

    Selects between:
    - 'handoff': For simple, linear, or real-time tasks (Low latency).
    - 'standard': For complex, multi-step, or quality-critical tasks (High robustness).
    - 'fast_path': For trivial queries (Instant).

    Returns a validated WorkflowStrategyOutput.
    """

    task: str = dspy.InputField(desc="The user's request or task")
    complexity_analysis: str = dspy.InputField(desc="Analysis of task complexity")

    strategy: WorkflowStrategyOutput = dspy.OutputField(
        desc="Workflow strategy with mode (handoff/standard/fast_path) and reasoning"
    )


class SimpleResponse(dspy.Signature):
    """Directly answer a simple task or query."""

    task: str = dspy.InputField(desc="The simple task or question")
    answer: str = dspy.OutputField(desc="Concise and accurate answer")


class GroupChatSpeakerSelection(dspy.Signature):
    """Select the next speaker in a group chat."""

    history: str = dspy.InputField(desc="The conversation history so far")
    participants: str = dspy.InputField(desc="List of available participants and their roles")
    last_speaker: str = dspy.InputField(desc="The name of the last speaker")

    next_speaker: str = dspy.OutputField(desc="The name of the next speaker, or 'TERMINATE' to end")
    reasoning: str = dspy.OutputField(desc="Reasoning for the selection")


class AgentInstructionSignature(dspy.Signature):
    """Generate instructions for an agent based on its role and context."""

    role: str = dspy.InputField(desc="The role of the agent (e.g., 'coder', 'researcher')")
    description: str = dspy.InputField(desc="Description of the agent's responsibilities")
    task_context: str = dspy.InputField(desc="Context of the current task or workflow")

    agent_instructions: str = dspy.OutputField(desc="Detailed system instructions for the agent")


class PlannerInstructionSignature(dspy.Signature):
    """Generate specialized instructions for the Planner/Orchestrator agent."""

    available_agents: str = dspy.InputField(desc="List of available agents and their descriptions")
    workflow_goal: str = dspy.InputField(desc="The goal of the current workflow")

    agent_instructions: str = dspy.OutputField(desc="Detailed instructions for the Planner agent")


class WorkflowNarration(dspy.Signature):
    """Transform raw workflow events into a user-friendly narrative."""

    events_log: str = dspy.InputField(desc="Chronological log of workflow events")
    narrative: str = dspy.OutputField(
        desc="Concise, natural language summary of the workflow execution"
    )


# Backward-compatible aliases
TypedQualityAssessment = QualityAssessment
TypedEnhancedRouting = EnhancedTaskRouting
TypedToolPlan = ToolPlan
TypedProgressEvaluation = ProgressEvaluation
TypedTaskAnalysis = TaskAnalysis
TypedWorkflowStrategy = WorkflowStrategy


# =============================================================================
# Handoff Signatures (merged from handoff_signatures.py)
# =============================================================================


class HandoffDecision(dspy.Signature):
    """Determine if and how to hand off work between agents.

    This signature helps the supervisor decide when a handoff is necessary,
    which agent should receive the work, and what context to pass along.
    """

    current_agent = dspy.InputField(desc="agent currently handling the task")
    work_completed = dspy.InputField(desc="detailed summary of work completed so far")
    remaining_work = dspy.InputField(desc="what still needs to be done to complete the task")
    available_agents = dspy.InputField(desc="agents available for handoff with their capabilities")
    agent_states = dspy.InputField(
        desc="current state and capacity of each agent (e.g., busy, available, specialized for this)"
    )

    should_handoff = dspy.OutputField(desc="yes or no - whether handoff is recommended")
    next_agent = dspy.OutputField(desc="which agent to hand off to if yes (empty if no)")
    handoff_context = dspy.OutputField(desc="key information the next agent needs to know")
    handoff_reason = dspy.OutputField(desc="why this handoff is necessary or beneficial")


class HandoffProtocol(dspy.Signature):
    """Structure the handoff package between agents with rich metadata.

    Creates a comprehensive handoff package that ensures the receiving agent
    has all necessary context, artifacts, objectives, and success criteria.
    """

    from_agent = dspy.InputField(desc="agent initiating the handoff")
    to_agent = dspy.InputField(desc="agent receiving the handoff")
    work_completed = dspy.InputField(desc="comprehensive summary of completed work")
    artifacts = dspy.InputField(desc="data, files, or results produced (JSON format)")
    remaining_objectives = dspy.InputField(
        desc="specific objectives the next agent should accomplish"
    )
    success_criteria = dspy.InputField(desc="how to measure successful completion")
    tool_requirements = dspy.InputField(desc="tools the next agent will need")

    handoff_package = dspy.OutputField(desc="complete structured handoff package with all metadata")
    quality_checklist = dspy.OutputField(
        desc="items the next agent should verify before continuing"
    )
    estimated_effort = dspy.OutputField(desc="expected complexity: simple, moderate, or complex")


class CapabilityMatching(dspy.Signature):
    """Match task requirements to agent capabilities for optimal routing.

    Analyzes task requirements against available agent capabilities to find
    the best match, identify gaps, and provide confidence scoring.
    """

    task_requirements = dspy.InputField(desc="what the task needs (skills, tools, knowledge)")
    agent_capabilities = dspy.InputField(desc="detailed capabilities of each available agent")
    current_context = dspy.InputField(desc="workflow state and execution history")
    tool_availability = dspy.InputField(desc="available tools and which agents have access to them")

    best_match = dspy.OutputField(desc="agent with the best capability match for this task")
    capability_gaps = dspy.OutputField(desc="required capabilities that are not available")
    fallback_agents = dspy.OutputField(
        desc="alternative agents if primary is unavailable (comma-separated)"
    )
    confidence = dspy.OutputField(desc="confidence score 0-10 in the capability match")


class EnhancedTaskRoutingWithHandoff(dspy.Signature):
    """Advanced task routing with handoff awareness and capability matching.

    Extends standard task routing with handoff strategy planning,
    quality gates, and checkpoint identification.
    """

    task = dspy.InputField(desc="task to be routed")
    team_capabilities = dspy.InputField(desc="detailed agent capabilities with execution history")
    available_tools = dspy.InputField(desc="tools and their current availability status")
    current_context = dspy.InputField(desc="workflow state, agent load, and recent patterns")
    handoff_history = dspy.InputField(desc="recent handoff patterns and their outcomes")

    assigned_to = dspy.OutputField(desc="primary agent(s) for initial work (comma-separated)")
    execution_mode = dspy.OutputField(desc="delegated, sequential, parallel, or adaptive")
    handoff_strategy = dspy.OutputField(
        desc="planned handoff checkpoints and triggers (e.g., 'after research, handoff to analyst')"
    )
    subtasks = dspy.OutputField(desc="task breakdown with handoff points marked")
    quality_gates = dspy.OutputField(
        desc="checkpoints requiring review before handoff or completion"
    )


class ProgressEvaluationWithHandoff(dspy.Signature):
    """Evaluate progress and determine handoff or continuation strategy.

    Monitors workflow progress and recommends whether to continue with
    current agent, hand off to another agent, or escalate for help.
    """

    original_task = dspy.InputField(desc="original user request")
    completed_work = dspy.InputField(desc="work completed so far with agent attribution")
    current_agent = dspy.InputField(desc="agent currently working on the task")
    current_status = dspy.InputField(desc="detailed status including any blockers or issues")
    handoff_options = dspy.InputField(
        desc="available agents for potential handoff with their capabilities"
    )

    next_action = dspy.OutputField(desc="continue, handoff, refine, complete, or escalate")
    handoff_recommendation = dspy.OutputField(
        desc="who to handoff to and why (if action is handoff)"
    )
    feedback = dspy.OutputField(desc="specific feedback for current agent or next agent")
    risk_assessment = dspy.OutputField(desc="potential issues or risks in the next steps")


class HandoffQualityAssessment(dspy.Signature):
    """Assess the quality of a handoff between agents.

    Evaluates whether a handoff was successful by checking if the receiving
    agent has all necessary context and can proceed effectively.
    """

    handoff_context = dspy.InputField(desc="the handoff package that was transferred")
    from_agent = dspy.InputField(desc="agent that initiated the handoff")
    to_agent = dspy.InputField(desc="agent that received the handoff")
    work_completed = dspy.InputField(desc="work done by the receiving agent after handoff")

    handoff_quality_score = dspy.OutputField(desc="quality score 0-10 for the handoff")
    context_completeness = dspy.OutputField(desc="was all necessary context provided (yes/no)")
    success_factors = dspy.OutputField(desc="what made this handoff successful")
    improvement_areas = dspy.OutputField(desc="what could be improved in future handoffs")


__all__ = [
    "AgentInstructionSignature",
    "CapabilityMatching",
    "EnhancedTaskRouting",
    "EnhancedTaskRoutingWithHandoff",
    "GroupChatSpeakerSelection",
    "HandoffDecision",
    "HandoffProtocol",
    "HandoffQualityAssessment",
    "PlannerInstructionSignature",
    "ProgressEvaluation",
    "ProgressEvaluationWithHandoff",
    "QualityAssessment",
    "SimpleResponse",
    "TaskAnalysis",
    "TaskRouting",
    "ToolPlan",
    "TypedEnhancedRouting",
    "TypedProgressEvaluation",
    "TypedQualityAssessment",
    "TypedTaskAnalysis",
    "TypedToolPlan",
    "TypedWorkflowStrategy",
    "WorkflowNarration",
    "WorkflowStrategy",
]
