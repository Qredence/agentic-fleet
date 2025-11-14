"""
DSPy Signatures for intelligent agent handoff workflows.

Provides specialized signatures for:
- Evaluating when handoffs are needed
- Structuring handoff context and metadata
- Matching tasks to agent capabilities
"""

from __future__ import annotations

import dspy


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


class EnhancedTaskRouting(dspy.Signature):
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
