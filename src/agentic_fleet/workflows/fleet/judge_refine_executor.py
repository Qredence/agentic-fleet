"""Judge and refinement executor for fleet workflow.

Handles judge evaluation and refinement loops using agent-framework agents.
"""

from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING, Any

from agent_framework import Executor, WorkflowContext

from ...utils.logger import setup_logger
from ...utils.models import ExecutionMode, RoutingDecision
from ..quality import call_judge_with_reasoning, parse_judge_response
from ..quality.criteria import get_quality_criteria as _get_quality_criteria
from .decorators import handler
from .messages import FinalResultMessage, QualityMessage

if TYPE_CHECKING:
    from ..orchestration import SupervisorContext

logger = setup_logger(__name__)


class JudgeRefineExecutor(Executor):
    """Executor that evaluates quality with judge and performs refinement loops."""

    def __init__(
        self,
        executor_id: str,
        context: SupervisorContext,
    ) -> None:
        """Initialize JudgeRefineExecutor.

        Args:
            executor_id: Unique executor identifier
            context: Supervisor context with configuration and state
        """
        super().__init__(id=executor_id)
        self.context = context

    @handler
    async def handle_quality(
        self,
        quality_msg: QualityMessage,
        ctx: WorkflowContext[FinalResultMessage],
    ) -> None:
        """Handle quality message and perform judge evaluation + refinement.

        Args:
            quality_msg: Quality message from previous executor
            ctx: Workflow context for sending messages
        """
        task = quality_msg.task
        result = quality_msg.result
        agents = self.context.agents or {}

        logger.info("Starting judge evaluation and refinement phase...")

        judge_evaluations: list[dict[str, Any]] = []
        refinement_performed = False
        current_result = result

        # Judge evaluation phase (if enabled)
        if self.context.config.enable_judge and "Judge" in agents:
            try:
                # Apply timeout guard if configured
                judge_timeout = getattr(self.context.config, "judge_timeout_seconds", None)
                if judge_timeout and judge_timeout > 0:
                    try:
                        judge_eval = await asyncio.wait_for(
                            self._run_judge_phase(task, current_result, agents),
                            timeout=judge_timeout,
                        )
                    except TimeoutError:
                        logger.warning(
                            f"Judge evaluation timed out after {judge_timeout}s, skipping refinement"
                        )
                        judge_eval = {
                            "score": 7.0,  # Default passing score
                            "refinement_needed": "no",
                            "missing_elements": "Timeout during evaluation",
                            "required_improvements": "",
                        }
                else:
                    judge_eval = await self._run_judge_phase(task, current_result, agents)
                judge_evaluations.append(judge_eval)

                # Stream intermediate judge evaluation as workflow output so that
                # the CLI can surface scores and feedback while refinement is ongoing.
                try:
                    await ctx.yield_output(
                        FinalResultMessage(
                            result=current_result,
                            routing=quality_msg.routing
                            if quality_msg.routing is not None
                            else RoutingDecision(
                                task=task,
                                assigned_to=tuple(agents.keys()),
                                mode=ExecutionMode.DELEGATED,
                                subtasks=(task,),
                                tool_requirements=(),
                                confidence=None,
                            ),
                            quality=quality_msg.quality,
                            judge_evaluations=judge_evaluations.copy(),
                            execution_summary={},
                            phase_timings=self.context.latest_phase_timings.copy(),
                            phase_status=self.context.latest_phase_status.copy(),
                            metadata={**quality_msg.metadata, "intermediate_judge": True},
                        )
                    )
                except Exception:
                    # Non-fatal: continue refinement even if streaming fails
                    logger.debug("Failed to stream intermediate judge evaluation", exc_info=True)

                logger.info(
                    f"Judge evaluation: score={judge_eval['score']}/10, "
                    f"refinement_needed={judge_eval['refinement_needed']}"
                )

                # Refinement loop
                refinement_rounds = 0
                while (
                    refinement_rounds < self.context.config.max_refinement_rounds
                    and judge_eval.get("refinement_needed", "no").lower() == "yes"
                    and judge_eval.get("score", 0.0) < self.context.config.judge_threshold
                ):
                    refinement_rounds += 1
                    logger.info(
                        f"Starting refinement round {refinement_rounds}/{self.context.config.max_refinement_rounds}"
                    )

                    # Determine refinement agent
                    refinement_agent_name = judge_eval.get("refinement_agent")
                    if not refinement_agent_name or refinement_agent_name not in agents:
                        refinement_agent_name = self._determine_refinement_agent(
                            judge_eval.get("missing_elements", "")
                        )

                    if refinement_agent_name not in agents:
                        logger.warning(
                            f"Refinement agent '{refinement_agent_name}' not available, skipping refinement"
                        )
                        break

                    # Build refinement task
                    refinement_task = self._build_refinement_task(current_result, judge_eval)

                    # Execute refinement using agent-framework's agent.run()
                    try:
                        refinement_agent = agents[refinement_agent_name]
                        refined_result = await refinement_agent.run(refinement_task)
                        current_result = str(refined_result) if refined_result else current_result
                        logger.info(f"Refinement completed by {refinement_agent_name}")
                        refinement_performed = True
                    except Exception as exc:
                        logger.exception(f"Refinement failed: {exc}")
                        break

                    # Re-evaluate with judge (with timeout guard)
                    judge_timeout = getattr(self.context.config, "judge_timeout_seconds", None)
                    if judge_timeout and judge_timeout > 0:
                        try:
                            judge_eval = await asyncio.wait_for(
                                self._run_judge_phase(task, current_result, agents),
                                timeout=judge_timeout,
                            )
                        except TimeoutError:
                            logger.warning(
                                f"Judge re-evaluation timed out after {judge_timeout}s, stopping refinement"
                            )
                            break
                    else:
                        judge_eval = await self._run_judge_phase(task, current_result, agents)
                    judge_evaluations.append(judge_eval)
                    logger.info(
                        f"Judge re-evaluation (round {refinement_rounds}): score={judge_eval['score']}/10, "
                        f"refinement_needed={judge_eval['refinement_needed']}"
                    )

                    # Stop refinement if threshold is met or judge says no more needed
                    judge_score = judge_eval.get("score", 0.0)
                    if judge_score >= self.context.config.judge_threshold:
                        logger.info(
                            f"Quality threshold met ({judge_score} >= {self.context.config.judge_threshold}), "
                            "stopping refinement"
                        )
                        break
                    elif judge_eval.get("refinement_needed", "no").lower() == "no":
                        logger.info("Judge determined no further refinement needed")
                        break

            except Exception as e:
                logger.exception(f"Judge/refinement phase failed: {e}")

        # Fallback refinement (if enabled and judge is disabled OR judge didn't evaluate)
        # Skip fallback if judge already evaluated and passed, even if it didn't refine
        judge_evaluated_and_passed = (
            self.context.config.enable_judge
            and judge_evaluations
            and judge_evaluations[-1].get("score", 0.0) >= self.context.config.judge_threshold
        )

        if (
            not refinement_performed
            and not judge_evaluated_and_passed
            and self.context.config.enable_refinement
            and quality_msg.quality.score < self.context.config.refinement_threshold
        ):
            logger.info(
                f"Quality below threshold ({self.context.config.refinement_threshold}), refining results..."
            )
            try:
                from ..quality import refine_results

                current_result = await refine_results(
                    current_result, quality_msg.quality.improvements, agents
                )
                refinement_performed = True
            except Exception as e:
                logger.exception(f"Refinement failed: {e}")

        # Update quality with final judge evaluation if available
        final_quality = quality_msg.quality
        if judge_evaluations:
            last_judge = judge_evaluations[-1]
            from ..shared.models import QualityReport

            final_quality = QualityReport(
                score=last_judge.get("score", final_quality.score),
                missing=final_quality.missing,
                improvements=final_quality.improvements,
                judge_score=last_judge.get("score"),
                final_evaluation=last_judge,
                used_fallback=final_quality.used_fallback,
            )

        # Get execution summary from supervisor
        execution_summary = {}
        if self.context.dspy_supervisor:
            execution_summary = self.context.dspy_supervisor.get_execution_summary()

        # Get routing decision from quality message or metadata
        routing_decision = quality_msg.routing
        if routing_decision is None and "routing" in quality_msg.metadata:
            routing_data = quality_msg.metadata["routing"]
            if isinstance(routing_data, RoutingDecision):
                routing_decision = routing_data
            elif isinstance(routing_data, dict):
                routing_decision = RoutingDecision.from_mapping(routing_data)

        # Fallback: create minimal routing decision if not available
        if routing_decision is None:
            routing_decision = RoutingDecision(
                task=task,
                assigned_to=(),
                mode=ExecutionMode.DELEGATED,
                subtasks=(),
                tool_requirements=(),
                confidence=None,
            )

        final_msg = FinalResultMessage(
            result=current_result,
            routing=routing_decision,
            quality=final_quality,
            judge_evaluations=judge_evaluations,
            execution_summary=execution_summary,
            phase_timings=self.context.latest_phase_timings.copy(),
            phase_status=self.context.latest_phase_status.copy(),
            metadata=quality_msg.metadata,
        )

        # Yield final output
        await ctx.yield_output(final_msg)

    async def _run_judge_phase(
        self,
        task: str,
        result: str,
        agents: dict[str, Any],
    ) -> dict[str, Any]:
        """Run judge evaluation phase."""
        from ..shared.quality import run_judge_phase

        async def get_quality_criteria_fn(task: str) -> str:
            return await _get_quality_criteria(
                task,
                agents,
                lambda agent, prompt: call_judge_with_reasoning(
                    agent, prompt, self.context.config.judge_reasoning_effort
                ),
            )

        def determine_refinement_agent_fn(missing_elements: str) -> str | None:
            return self._determine_refinement_agent(missing_elements)

        def record_status(phase: str, status: str) -> None:
            self.context.latest_phase_status[phase] = status

        return await run_judge_phase(
            task=task,
            result=result,
            agents=agents,
            config=self.context.config,
            get_quality_criteria_fn=get_quality_criteria_fn,
            parse_judge_response_fn=parse_judge_response,
            determine_refinement_agent_fn=determine_refinement_agent_fn,
            record_status=record_status,
        )

    def _determine_refinement_agent(self, missing_elements: str) -> str | None:
        """Determine which agent should handle refinement based on missing elements."""
        missing_lower = missing_elements.lower() if missing_elements else ""

        # Map missing elements to appropriate agents (matching supervisor_workflow logic)
        if (
            "citation" in missing_lower
            or "source" in missing_lower
            or "link" in missing_lower
            or "url" in missing_lower
        ):
            return "Researcher"  # Researcher has TavilyMCPTool for citations
        elif (
            "vote" in missing_lower
            or "total" in missing_lower
            or "percentage" in missing_lower
            or "calculation" in missing_lower
            or "code" in missing_lower
            or "data" in missing_lower
            or "analysis" in missing_lower
        ):
            return "Analyst"  # Analyst has HostedCodeInterpreterTool
        elif (
            "write" in missing_lower
            or "content" in missing_lower
            or "structure" in missing_lower
            or "clarity" in missing_lower
            or "format" in missing_lower
        ):
            return "Writer"
        else:
            # Default to Writer for general improvements
            return "Writer"

    def _build_refinement_task(self, current_result: str, judge_eval: dict[str, Any]) -> str:
        """Build refinement task from judge evaluation."""
        missing = judge_eval.get("missing_elements", "")
        improvements = judge_eval.get("required_improvements", "") or judge_eval.get(
            "improvements", ""
        )

        refinement_prompt = f"""Refine the following response based on the judge's evaluation.

Current Response:
{current_result}

Missing Elements:
{missing}

Required Improvements:
{improvements}

Please refine the response to address the missing elements and incorporate the required improvements.
Ensure the refined response is complete, accurate, and meets all quality criteria."""

        return refinement_prompt
