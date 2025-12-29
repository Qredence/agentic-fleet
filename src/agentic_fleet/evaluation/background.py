"""Background quality evaluation for completed workflow runs.

Runs post-hoc evaluation in the background (off the critical path) so the user
doesn't wait for potentially slow scoring/evaluation calls.

This updates:
- execution history (HistoryManager) for the workflowId
- persisted conversation message (ConversationManager) when IDs are provided
"""

from __future__ import annotations

import asyncio
from typing import Any

from agentic_fleet.utils.infra.logging import setup_logger

logger = setup_logger(__name__)


def sanitize_for_log(value: str | None) -> str:
    """Sanitize a string so it is safe for log entry: remove line breaks/CR."""
    if value is None:
        return ""
    return str(value).replace("\r\n", "").replace("\n", "").replace("\r", "")


# Retain task references to prevent premature GC (ruff RUF006 style).
_background_tasks: set[asyncio.Task[Any]] = set()


def _score_0_to_10(metrics: dict[str, Any]) -> float:
    try:
        score_0_to_1 = float(metrics.get("quality_score", 0.0) or 0.0)
    except Exception:
        score_0_to_1 = 0.0
    return max(0.0, min(10.0, round(score_0_to_1 * 10.0, 1)))


def schedule_quality_evaluation(
    *,
    workflow_id: str,
    task: str,
    answer: str,
    history_manager: Any | None = None,
    conversation_manager: Any | None = None,
    conversation_id: str | None = None,
    message_id: str | None = None,
) -> None:
    """Schedule quality evaluation in the background.

    This is fire-and-forget by design. Failures are logged and do not impact
    the user-visible request.
    """

    async def _run() -> None:
        try:
            if not task.strip() or not answer.strip():
                logger.debug(
                    "Skipping quality evaluation: empty task or answer (workflow_id=%s)",
                    workflow_id,
                )
                return

            from agentic_fleet.dspy_modules.answer_quality import score_answer_with_dspy

            metrics = await asyncio.to_thread(score_answer_with_dspy, task, answer)
            score = _score_0_to_10(metrics)
            flag = metrics.get("quality_flag") if isinstance(metrics, dict) else None

            # Log quality evaluation results for debugging
            logger.info(
                "Quality evaluation complete (workflow_id=%s, score=%.1f/10, flag=%s)",
                workflow_id,
                score,
                flag or "none",
            )

            details = {
                "answer_quality": {
                    "groundness": metrics.get("quality_groundness"),
                    "relevance": metrics.get("quality_relevance"),
                    "coherence": metrics.get("quality_coherence"),
                    "scale": "0-1",
                }
            }

            if history_manager is not None:
                patch = {
                    "quality": {
                        "score": score,
                        "flag": flag,
                        "final_evaluation": details,
                        "pending": False,
                    }
                }
                try:
                    await asyncio.to_thread(history_manager.update_execution, workflow_id, patch)
                except Exception as exc:
                    logger.debug(
                        "History quality update failed (workflow_id=%s): %s", workflow_id, exc
                    )

            if conversation_manager is not None and conversation_id and message_id:
                try:
                    await asyncio.to_thread(
                        conversation_manager.update_message,
                        conversation_id,
                        message_id,
                        quality_score=score,
                        quality_flag=str(flag) if flag else None,
                        quality_pending=False,
                        quality_details=details,
                    )
                except Exception as exc:
                    logger.debug(
                        "Conversation quality update failed (conversation_id=%s, message_id=%s): %s",
                        sanitize_for_log(conversation_id),
                        sanitize_for_log(message_id),
                        exc,
                    )
        except Exception as exc:
            logger.error(
                "Background evaluation failed (workflow_id=%s): %s",
                workflow_id,
                exc,
                exc_info=True,
            )

    task_obj = asyncio.create_task(_run())
    _background_tasks.add(task_obj)
    task_obj.add_done_callback(_background_tasks.discard)


__all__ = ["schedule_quality_evaluation"]
