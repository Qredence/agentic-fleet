"""
DSPy Signatures for intelligent workflow orchestration.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol

import dspy

if TYPE_CHECKING:  # pragma: no cover - typing helper

    class SignatureBase(Protocol): ...

    class _Field:
        def __init__(self, desc: str = ""): ...

    InputField = _Field
    OutputField = _Field
else:  # pragma: no cover - runtime path
    SignatureBase = dspy.Signature
    InputField = dspy.InputField
    OutputField = dspy.OutputField


class TaskRouting(SignatureBase):
    """Determine optimal routing for a task (handoff-aware).

    This signature routes tasks to appropriate agents with correct execution mode.
    Follow the step-by-step process below to make accurate routing decisions.

    PROCESS STEPS:
    1. Analyze task requirements: What capabilities are needed? (research, analysis, writing, review)
    2. Check tool requirements: Does task need web search, code execution, or no tools?
    3. Determine execution mode:
       - delegated: Simple, single-agent tasks (e.g., "What is X?", "Write a paragraph about Y")
       - sequential: Multi-step tasks with dependencies (e.g., "Research X, then analyze results, then write report")
       - parallel: Multiple independent subtasks (e.g., "Research topic A and topic B simultaneously")
    4. Match agents to capabilities: Researcher for research, Analyst for data/code, Writer for content, Reviewer for validation
    5. Verify tool availability: Ensure assigned agents have access to required tools

    EDGE CASE GUIDANCE:
    - Ambiguous tasks ("maybe", "could", "either/or"): Default to Researcher for clarification, use delegated mode
    - Time-sensitive queries ("latest", "current", "today", "2025", "future"): Always require TavilySearchTool → assign Researcher
    - Multi-part tasks with "and"/"also"/"then": Check if parts are independent (parallel) or dependent (sequential)
    - Tasks requiring both research AND analysis: Use sequential mode (Researcher → Analyst)
    - Tasks requiring research, analysis, AND writing: Use sequential mode (Researcher → Analyst → Writer)

    CLARIFYING EXAMPLES:
    - "What is the latest news about AI?" → Researcher, delegated, TavilySearchTool (time-sensitive)
    - "Research X and analyze Y" → Researcher+Analyst, parallel (independent subtasks)
    - "Research X, then analyze results" → Researcher+Analyst, sequential (dependent steps)
    - "Write a blog post about Python" → Writer, delegated, no tools (simple writing task)
    - "Calculate the average of [1,2,3,4,5]" → Analyst, delegated, HostedCodeInterpreterTool (computation)
    - "Review this document for errors" → Reviewer, delegated, no tools (validation task)

    COMMON MISTAKES TO AVOID:
    - Don't assign Researcher for simple factual questions that don't need web search
    - Don't use parallel mode when subtasks have dependencies (use sequential instead)
    - Don't assign tools to agents that don't have access (check available_tools)
    - Don't over-assign agents for simple tasks (use delegated mode for single-agent tasks)
    - Don't miss TavilySearchTool for time-sensitive queries (check for "latest", "current", dates)
    """

    task = InputField(desc="task to be routed")
    team_capabilities = InputField(desc="available team members and their skills")
    available_tools = InputField(desc="available tools and their capabilities")
    current_context = InputField(desc="current workflow state and history")
    handoff_history = InputField(desc="recent handoff patterns and outcomes")
    assigned_to = OutputField(
        desc="team member(s) to handle the task (comma-separated if multiple)"
    )
    execution_mode = OutputField(
        desc="parallel|sequential|delegated - use delegated for single-agent tasks, sequential for dependent steps, parallel for independent subtasks"
    )
    subtasks = OutputField(
        desc="breakdown if parallel execution needed (one per line), empty if delegated"
    )
    confidence = OutputField(desc="confidence score (0-1) for the routing decision")


class TaskAnalysis(SignatureBase):
    """Analyze task complexity and requirements.

    This signature analyzes tasks to determine their complexity, required capabilities,
    and tool needs. Follow the analysis process below for accurate assessment.

    ANALYSIS PROCESS:
    1. Identify task type: research, analysis, writing, review, or combination
    2. Assess complexity:
       - simple: Single-step, single-agent tasks (e.g., "What is X?", "Write one paragraph")
       - moderate: Multi-step but clear path (e.g., "Research X and summarize")
       - complex: Multi-agent coordination needed (e.g., "Research X, analyze Y, write comprehensive report")
    3. Determine capabilities: Match task needs to agent capabilities (research, data analysis, writing, validation)
    4. Identify tool requirements: Check if task needs web search, code execution, or no tools

    TASK-SPECIFIC PATTERNS:
    - Research tasks: Require Researcher capability, often need TavilySearchTool for current information
    - Analysis tasks: Require Analyst capability, often need HostedCodeInterpreterTool for calculations
    - Writing tasks: Require Writer capability, typically no tools needed
    - Review tasks: Require Reviewer capability, typically no tools needed
    - Combined tasks: Require multiple capabilities, estimate steps based on dependencies

    EDGE CASE GUIDANCE:
    - Ambiguous tasks: Mark as moderate complexity, include Researcher in capabilities
    - Time-sensitive queries: Always require TavilySearchTool (check for "latest", "current", dates)
    - Multi-part tasks: Count each independent part as a step
    - Tasks with dependencies: Count sequential steps (e.g., research→analysis→writing = 3 steps)
    """

    task = InputField(desc="user task to analyze")
    complexity = OutputField(
        desc="simple|moderate|complex - simple for single-step tasks, moderate for multi-step, complex for multi-agent coordination"
    )
    required_capabilities = OutputField(
        desc="list of required agent capabilities (comma-separated): research, analysis, writing, review"
    )
    tool_requirements = OutputField(
        desc="tools needed for this task (comma-separated): TavilySearchTool for web search, HostedCodeInterpreterTool for code execution, empty if none"
    )
    estimated_steps = OutputField(
        desc="number of steps needed (1 for simple, 2-3 for moderate, 4+ for complex)"
    )


class ProgressEvaluation(SignatureBase):
    """Evaluate workflow progress and determine next steps."""

    original_task = InputField(desc="original user request")
    completed_work = InputField(desc="work completed so far")
    current_status = InputField(desc="current workflow status")
    next_action = OutputField(desc="continue|refine|complete|escalate")
    feedback = OutputField(desc="specific feedback for team")


class QualityAssessment(SignatureBase):
    """Assess quality of results and determine if requirements are met."""

    requirements = InputField(desc="original requirements")
    results = InputField(desc="produced results")
    quality_score = OutputField(desc="score from 1-10")
    missing_elements = OutputField(desc="what's missing if incomplete")
    improvement_suggestions = OutputField(desc="how to improve if needed")


class ResearchStrategy(SignatureBase):
    """Determine research strategy for a given topic."""

    topic = InputField(desc="research topic or question")
    context = InputField(desc="available resources and constraints")
    strategy = OutputField(desc="step-by-step research approach")
    search_queries = OutputField(desc="list of specific search queries")


class DataAnalysisPlan(SignatureBase):
    """Plan computational analysis for research findings."""

    research_findings = InputField(desc="collected research data")
    analysis_goals = InputField(desc="what to analyze or compute")
    code_plan = OutputField(desc="structured plan for code implementation")
    expected_outputs = OutputField(desc="expected analysis outputs")


class SynthesisStrategy(SignatureBase):
    """Synthesize research and analysis into conclusions."""

    research_data = InputField(desc="research findings")
    analysis_results = InputField(desc="computational results")
    synthesis = OutputField(desc="integrated conclusions and recommendations")


class ToolAwareTaskAnalysis(SignatureBase):
    """Analyze task with tool usage awareness.

    This signature analyzes tasks with explicit awareness of available tools.
    Use this when tools are available to make better routing decisions.

    ANALYSIS PROCESS:
    1. Check if task needs current/real-time information:
       - Keywords: "latest", "current", "recent", "today", "now", specific dates/years (2025, 2026, etc.)
       - If yes: needs_web_search = "yes", generate search_query
       - If no: needs_web_search = "no", search_query = ""
    2. Assess complexity and capabilities (same as TaskAnalysis)
    3. Match tool requirements to available tools:
       - Web search needs → TavilySearchTool (if available)
       - Code execution needs → HostedCodeInterpreterTool (if available)
    4. Estimate steps considering tool usage (tool calls add steps)

    EDGE CASE GUIDANCE:
    - Future dates/years: Always require web search (e.g., "2025 election", "next year's forecast")
    - "Latest" or "current" without explicit dates: Still require web search (information may be outdated)
    - Ambiguous time references ("recent", "now"): Require web search to be safe
    - Historical facts before training cutoff: May not need web search (use judgment)
    - Tasks with "calculate" or "analyze data": Check if HostedCodeInterpreterTool is needed

    CLARIFYING EXAMPLES:
    - "What is the latest news?" → needs_web_search=yes, search_query="latest news"
    - "What happened in 2020?" → needs_web_search=no (historical, before cutoff)
    - "What will happen in 2026?" → needs_web_search=yes, search_query="2026 predictions"
    - "Calculate 2+2" → needs_web_search=no, but needs HostedCodeInterpreterTool
    - "What is Python?" → needs_web_search=no (general knowledge)
    """

    task = InputField(desc="user task to analyze")
    available_tools = InputField(desc="available tools and their capabilities")
    needs_web_search = OutputField(
        desc="whether task requires web search (yes/no). Say YES for: current events, recent news, latest data, future predictions, real-time information, facts beyond model's training cutoff date, or when user asks about 'latest', 'current', 'recent', 'today', specific future dates/years"
    )
    search_query = OutputField(
        desc="search query if web search is needed (specific and focused), empty otherwise"
    )
    complexity = OutputField(
        desc="simple|moderate|complex - simple for single-step tasks, moderate for multi-step, complex for multi-agent coordination"
    )
    required_capabilities = OutputField(
        desc="list of required agent capabilities (comma-separated): research, analysis, writing, review"
    )
    tool_requirements = OutputField(
        desc="tools needed for this task (comma-separated): TavilySearchTool for web search, HostedCodeInterpreterTool for code execution, empty if none"
    )
    estimated_steps = OutputField(
        desc="number of steps needed (1 for simple, 2-3 for moderate, 4+ for complex)"
    )
