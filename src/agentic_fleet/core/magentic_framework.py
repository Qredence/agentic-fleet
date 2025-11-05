"""
Magentic Workflow Framework Integration

Properly implements Microsoft Agent Framework's Magentic pattern:
https://github.com/microsoft/agent-framework/blob/main/python/packages/core/agent_framework/_workflows/_magentic.py

Core workflow cycle: PLAN → EVALUATE → ACT → OBSERVE → (repeat or complete)
"""

import logging
from collections.abc import AsyncIterator, Callable
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, cast, no_type_check

from agent_framework import ChatAgent, ai_function
from agent_framework.openai import OpenAIResponsesClient
from pydantic import BaseModel, Field

from agentic_fleet.models.events import WorkflowEvent

logger = logging.getLogger(__name__)


class MagenticPhase(Enum):
    """Phases of Magentic workflow execution"""

    PLAN = "plan"
    EVALUATE = "evaluate"
    ACT = "act"
    OBSERVE = "observe"
    COMPLETE = "complete"


@dataclass
class MagenticContext:
    """
    Context for Magentic workflow execution.
    Tracks state across the PLAN → EVALUATE → ACT → OBSERVE cycle.
    """

    task: str
    current_phase: MagenticPhase = MagenticPhase.PLAN
    plan: str | None = None
    progress_ledger: dict[str, Any] = field(default_factory=dict)
    observations: list[str] = field(default_factory=list)
    round_count: int = 0
    stall_count: int = 0
    reset_count: int = 0
    max_rounds: int = 30
    max_stalls: int = 3
    max_resets: int = 2


class ProgressLedger(BaseModel):
    """Structured progress evaluation from manager agent"""

    request_satisfied: bool = Field(description="Is the original request fully satisfied?")
    in_infinite_loop: bool = Field(description="Are we stuck in a repetitive pattern?")
    making_progress: bool = Field(description="Are we making forward progress toward the goal?")
    next_agent: str = Field(description="Which specialist agent should act next?")
    instruction: str = Field(description="Specific instruction for the next agent")


class MagenticOrchestrator:
    """
    Magentic orchestrator following Microsoft Agent Framework patterns.

    Implements the core Magentic workflow cycle:
    1. PLAN: Analyze task, identify known/unknown, create action plan
    2. EVALUATE: Create progress ledger, check satisfaction and progress
    3. ACT: Delegate to specialist agent with specific instruction
    4. OBSERVE: Review response, update context, decide next action

    The manager coordinates all specialist agents and maintains workflow state.
    """

    def __init__(self, config: Any, event_bus: Any | None = None):
        """
        Initialize Magentic orchestrator.

        Args:
            config: Workflow configuration with fleet settings
            event_bus: Optional event bus for publishing events
        """
        self.config = config
        self.event_bus = event_bus
        self.client = self._create_client()
        self.manager_agent = self._create_manager()
        self.specialist_agents = self._create_specialists()

    def _create_client(self) -> OpenAIResponsesClient:
        """Create OpenAI client following framework patterns"""
        import os

        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError("OPENAI_API_KEY environment variable is required")
        return OpenAIResponsesClient(model=self.config.fleet.manager.model, api_key=api_key)

    def _create_manager(self) -> ChatAgent:
        """
        Create manager agent with Magentic orchestration instructions.

        The manager is the central coordinator that:
        - Creates plans by analyzing tasks
        - Evaluates progress at each round
        - Selects appropriate specialist agents
        - Decides when the task is complete
        """
        instructions = """You are the Orchestrator, the central coordinator of a multi-agent system.

Your workflow follows the Magentic pattern with four phases:

1. PLAN Phase:
   - Analyze the task deeply
   - Identify what information is already known
   - Determine what information needs to be gathered
   - Create a structured action plan with clear milestones
   - Consider dependencies and sequencing

2. EVALUATE Phase:
   - Review all observations and progress so far
   - Assess if the original request is satisfied
   - Check if we're making forward progress or stuck in a loop
   - Decide which specialist agent should act next
   - Provide a specific, actionable instruction for that agent
   - Use the evaluate_progress function to create a structured ledger

3. ACT Phase:
   - The selected specialist agent executes with your instruction
   - You observe their response

4. OBSERVE Phase:
   - Analyze the specialist's response
   - Update your understanding of the situation
   - Prepare for the next evaluation cycle

Available Specialist Agents:
- coordinator: High-level task coordination and delegation
- planner: Creates detailed execution plans and strategies
- executor: Runs code and commands in a safe environment
- generator: Generates code, content, and documentation
- verifier: Validates outputs, checks quality and correctness
- coder: Writes, reviews, and tests code implementations

Guidelines:
- Be decisive and specific in your instructions to agents
- Avoid vague instructions like "continue" or "proceed"
- If stuck, try a different agent or approach
- Consider parallel work when tasks are independent
- Always check if the original request is fully satisfied
- Provide clear success criteria in your instructions
"""

        return self.client.create_agent(
            name="MagenticOrchestrator",
            instructions=instructions,
            tools=[self._create_progress_evaluator_tool()],
        )

    def _create_progress_evaluator_tool(self) -> Any:
        """Create the evaluate_progress tool for the manager agent"""

        @no_type_check
        @ai_function
        def evaluate_progress(
            request_satisfied: bool,
            in_infinite_loop: bool,
            making_progress: bool,
            next_agent: str,
            instruction: str,
        ) -> dict[str, Any]:
            """
            Evaluate current progress and decide next action.

            Args:
                request_satisfied: Is the original request fully satisfied?
                in_infinite_loop: Are we stuck in a repetitive pattern?
                making_progress: Are we making forward progress?
                next_agent: Which specialist agent should act next?
                instruction: Specific instruction for the next agent

            Returns:
                Progress ledger dictionary
            """
            return {
                "request_satisfied": request_satisfied,
                "in_infinite_loop": in_infinite_loop,
                "making_progress": making_progress,
                "next_agent": next_agent,
                "instruction": instruction,
            }

        return evaluate_progress

    def _create_specialists(self) -> dict[str, ChatAgent]:
        """
        Create specialist agents from configuration.

        Loads agent factories and creates instances based on YAML config.
        """
        agents: dict[str, ChatAgent] = {}

        # Import agent factories (if available). These factories are optional, so we
        # attempt a dynamic import and gracefully fall back to basic ChatAgent
        # instances when functions are absent.
        try:
            import importlib

            agents_module = importlib.import_module("agentic_fleet.agents")
        except ImportError as exc:
            logger.warning(f"Could not import agent factories: {exc}")
        else:
            factory_attribute_names = {
                "coordinator": "create_coordinator_agent",
                "planner": "create_planner_agent",
                "executor": "create_executor_agent",
                "generator": "create_generator_agent",
                "verifier": "create_verifier_agent",
                "coder": "create_coder_agent",
            }

            agent_creators: dict[str, Callable[[Any], ChatAgent]] = {}
            for agent_key, attr_name in factory_attribute_names.items():
                creator = getattr(agents_module, attr_name, None)
                if callable(creator):
                    agent_creators[agent_key] = cast(Callable[[Any], ChatAgent], creator)

            for agent_name in self.config.fleet.agents:
                creator = agent_creators.get(agent_name)
                if creator is None:
                    continue
                try:
                    agents[agent_name] = creator(self.config)
                    logger.info(f"Created specialist agent: {agent_name}")
                except Exception as exc:  # pragma: no cover - defensive logging
                    logger.warning(
                        "Failed to create specialist agent '%s' via factory: %s",
                        agent_name,
                        exc,
                    )

        # Fallback: create basic agents for any remaining identifiers
        for agent_name in self.config.fleet.agents:
            if agent_name in agents:
                continue
            agents[agent_name] = self.client.create_agent(
                name=agent_name.title(),
                instructions=f"You are a {agent_name} specialist agent.",
            )

        return agents

    async def execute(
        self, task: str, context: MagenticContext | None = None
    ) -> AsyncIterator[WorkflowEvent]:
        """
        Execute Magentic workflow with streaming events.

        Follows the PLAN → EVALUATE → ACT → OBSERVE cycle until:
        - Task is satisfied (success)
        - Max rounds reached (timeout)
        - Max resets exceeded (failure)

        Args:
            task: The task to execute
            context: Optional existing context to continue from

        Yields:
            WorkflowEvent objects for each significant event
        """
        if context is None:
            context = MagenticContext(
                task=task,
                max_rounds=self.config.fleet.orchestrator.max_round_count,
                max_stalls=self.config.fleet.orchestrator.max_stall_count,
                max_resets=self.config.fleet.orchestrator.max_reset_count,
            )

        logger.info(f"Starting Magentic workflow for task: {task}")
        yield WorkflowEvent(
            type="workflow_start", data={"task": task, "max_rounds": context.max_rounds}
        )

        while context.round_count < context.max_rounds:
            context.round_count += 1

            # Emit round start event
            yield WorkflowEvent(
                type="round_start",
                data={"round": context.round_count, "phase": context.current_phase.value},
            )

            try:
                # Execute current phase
                if context.current_phase == MagenticPhase.PLAN:
                    await self._plan_phase(context)
                    yield WorkflowEvent(type="plan_created", data={"plan": context.plan})
                    context.current_phase = MagenticPhase.EVALUATE

                elif context.current_phase == MagenticPhase.EVALUATE:
                    evaluation = await self._evaluate_phase(context)
                    yield WorkflowEvent(type="evaluation_complete", data=evaluation)

                    if evaluation["request_satisfied"]:
                        context.current_phase = MagenticPhase.COMPLETE
                        yield WorkflowEvent(
                            type="workflow_complete",
                            data={"rounds": context.round_count, "success": True},
                        )
                        break

                    if evaluation["in_infinite_loop"]:
                        context.stall_count += 1
                        if context.stall_count >= context.max_stalls:
                            yield WorkflowEvent(
                                type="workflow_stalled", data={"stall_count": context.stall_count}
                            )
                            await self._reset_workflow(context)
                            yield WorkflowEvent(
                                type="workflow_reset", data={"reset_count": context.reset_count}
                            )
                            continue
                    else:
                        # Making progress, reset stall counter
                        context.stall_count = 0

                    context.current_phase = MagenticPhase.ACT
                    context.progress_ledger = evaluation

                elif context.current_phase == MagenticPhase.ACT:
                    response = await self._act_phase(context)
                    context.observations.append(response)
                    yield WorkflowEvent(
                        type="agent_response",
                        data={
                            "agent": context.progress_ledger.get("next_agent"),
                            "response": response[:500],  # Truncate for event
                        },
                    )
                    context.current_phase = MagenticPhase.OBSERVE

                elif context.current_phase == MagenticPhase.OBSERVE:
                    await self._observe_phase(context)
                    yield WorkflowEvent(
                        type="observation_complete",
                        data={"observations_count": len(context.observations)},
                    )
                    context.current_phase = MagenticPhase.EVALUATE

                # Emit phase complete event
                yield WorkflowEvent(
                    type="phase_complete",
                    data={"phase": context.current_phase.value, "round": context.round_count},
                )

            except Exception as e:
                logger.error(f"Error in phase {context.current_phase}: {e}", exc_info=True)
                yield WorkflowEvent(
                    type="error",
                    data={
                        "error": str(e),
                        "phase": context.current_phase.value,
                        "round": context.round_count,
                    },
                )

                # Attempt recovery
                if context.reset_count < context.max_resets:
                    await self._reset_workflow(context)
                    yield WorkflowEvent(
                        type="workflow_reset",
                        data={"reset_count": context.reset_count, "reason": "error"},
                    )
                else:
                    yield WorkflowEvent(
                        type="workflow_failed",
                        data={"reason": "max_resets_exceeded", "rounds": context.round_count},
                    )
                    raise

        # Max rounds reached without completion
        if context.current_phase != MagenticPhase.COMPLETE:
            yield WorkflowEvent(
                type="workflow_timeout",
                data={"rounds": context.round_count, "phase": context.current_phase.value},
            )

    async def _plan_phase(self, context: MagenticContext) -> None:
        """
        PLAN Phase: Create initial plan for the task.

        The manager analyzes the task and creates a structured plan
        with clear milestones and action items.
        """
        logger.info(f"PLAN phase - Round {context.round_count}")

        prompt = f"""Create a detailed plan for this task:
Task: {context.task}

Consider:
1. What information do we already know?
2. What information do we need to gather?
3. What actions need to be taken?
4. What is the logical sequence of steps?
5. What are the success criteria?

Provide a structured plan with clear, actionable milestones."""

        response = await self.manager_agent.run(prompt)
        # response.content attribute exists on agent framework responses.
        context.plan = getattr(response, "content", None)

        logger.info(f"Plan created: {context.plan[:200] if context.plan else 'None'}...")

        # Publish event if event bus available
        if self.event_bus:
            await self.event_bus.publish(
                WorkflowEvent(type="plan_created", data={"plan": context.plan})
            )

    async def _evaluate_phase(self, context: MagenticContext) -> dict[str, Any]:
        """
        EVALUATE Phase: Assess progress and decide next action.

        The manager reviews all observations, checks progress,
        and creates a progress ledger using the evaluate_progress tool.
        """
        logger.info(f"EVALUATE phase - Round {context.round_count}")

        prompt = f"""Evaluate our progress on this task:

Original Task: {context.task}

Current Plan:
{context.plan}

Observations so far ({len(context.observations)} total):
{self._format_observations(context.observations)}

Using the evaluate_progress function, create a progress ledger with:
- request_satisfied: Is the task fully complete?
- in_infinite_loop: Are we stuck in a repetitive pattern?
- making_progress: Are we advancing toward the goal?
- next_agent: Which specialist should act next?
- instruction: Specific, actionable task for that agent

Be honest about progress. If stuck, try a different approach or agent."""

        response = await self.manager_agent.run(prompt)

        # Extract evaluation from tool call
        tool_calls = getattr(response, "tool_calls", None)
        if tool_calls:
            evaluation = cast(dict[str, Any], tool_calls[0].result)
            logger.info(
                f"Evaluation: satisfied={evaluation.get('request_satisfied')}, "
                f"loop={evaluation.get('in_infinite_loop')}, "
                f"progress={evaluation.get('making_progress')}, "
                f"next={evaluation.get('next_agent')}"
            )
            return evaluation
        else:
            # Fallback if no tool call
            logger.warning("No tool call in evaluation, using defaults")
            return {
                "request_satisfied": False,
                "in_infinite_loop": False,
                "making_progress": True,
                "next_agent": "coordinator",
                "instruction": "Continue with the task",
            }

    async def _act_phase(self, context: MagenticContext) -> str:
        """
        ACT Phase: Execute action with selected agent.

        The specialist agent performs the specific task
        defined in the progress ledger instruction.
        """
        agent_name = context.progress_ledger.get("next_agent", "coordinator")
        instruction = context.progress_ledger.get("instruction", "")

        logger.info(f"ACT phase - Round {context.round_count}, Agent: {agent_name}")

        if agent_name not in self.specialist_agents:
            logger.error(f"Unknown agent: {agent_name}")
            return f"Error: Unknown agent '{agent_name}'. Available: {list(self.specialist_agents.keys())}"

        agent = self.specialist_agents[agent_name]

        # Publish agent start event
        if self.event_bus:
            await self.event_bus.publish(
                WorkflowEvent(
                    type="agent_start", data={"agent": agent_name, "instruction": instruction}
                )
            )

        # Execute with agent
        try:
            response = await agent.run(instruction)
            # Tool/agent responses supply a .content attribute; treat as str.
            result = getattr(response, "content", "")

            logger.info(f"Agent {agent_name} response: {result[:200] if result else 'None'}...")

            # Publish agent complete event
            if self.event_bus:
                await self.event_bus.publish(
                    WorkflowEvent(
                        type="agent_complete", data={"agent": agent_name, "response": result}
                    )
                )

            return result

        except Exception as e:
            logger.error(f"Agent {agent_name} error: {e}", exc_info=True)
            return f"Agent {agent_name} encountered an error: {e!s}"

    async def _observe_phase(self, context: MagenticContext) -> None:
        """
        OBSERVE Phase: Process latest observation and update context.

        The manager reviews the specialist's response and
        prepares for the next evaluation cycle.
        """
        logger.info(f"OBSERVE phase - Round {context.round_count}")

        latest = context.observations[-1] if context.observations else ""

        prompt = f"""Based on this latest response from {context.progress_ledger.get("next_agent")}:

{latest}

Brief assessment:
1. Was the instruction completed successfully?
2. What new information do we have?
3. Should we continue with the current plan or adjust?

Provide a concise analysis to prepare for the next evaluation."""

        response = await self.manager_agent.run(prompt)

        content = getattr(response, "content", None)
        logger.info(f"Observation assessment: {content[:200] if content else 'None'}...")

        # The assessment helps inform the next evaluation
        # Could update plan or context based on critical observations

    async def _reset_workflow(self, context: MagenticContext) -> None:
        """
        Reset workflow when stuck or after error.

        Clears observations, resets phase to PLAN,
        and attempts to create a fresh approach.
        """
        logger.warning(f"Resetting workflow (reset #{context.reset_count + 1})")

        context.reset_count += 1
        context.stall_count = 0
        context.current_phase = MagenticPhase.PLAN

        # Keep observations for context but clear plan for fresh approach
        context.plan = None

        # Publish reset event
        if self.event_bus:
            await self.event_bus.publish(
                WorkflowEvent(type="workflow_reset", data={"reset_count": context.reset_count})
            )

    def _format_observations(self, observations: list[str]) -> str:
        """Format observations for context inclusion"""
        if not observations:
            return "No observations yet."

        # Show last 5 observations to avoid context overflow
        recent = observations[-5:]
        formatted = []

        for i, obs in enumerate(recent, start=len(observations) - len(recent) + 1):
            # Truncate long observations
            truncated = obs[:300] + "..." if len(obs) > 300 else obs
            formatted.append(f"{i}. {truncated}")

        return "\n".join(formatted)
