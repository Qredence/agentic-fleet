"""Router agent that emits routing metadata."""

from __future__ import annotations

from typing import Any

from agent_framework import AgentRunResponse, ChatMessage, Role

from agentic_fleet.agents.base import BaseFleetAgent
from agentic_fleet.dspy_modules.signatures import RouterSignature
from agentic_fleet.middleware.context import ContextModulator


_ROUTE_PATTERN_NORMALIZATION = {
    "direct_answer": "direct",
    "simple_tool": "simple",
    "complex_council": "complex",
}


def _normalize_route_pattern(value: str) -> str:
    lowered = value.lower()
    return _ROUTE_PATTERN_NORMALIZATION.get(lowered, lowered)


class RouterAgent(BaseFleetAgent):
    """Generate routing decisions and attach them to the response metadata."""

    def __init__(self) -> None:
        super().__init__(
            name="Router",
            role="dispatcher",
            brain_signature=RouterSignature,
            model_role="router",
        )

    async def run(
        self,
        messages: str | ChatMessage | list[str] | list[ChatMessage] | None = None,
        *,
        metadata: dict[str, Any] | None = None,
        context: Any | None = None,
        team_id: str | None = None,
        **kwargs: Any,
    ) -> AgentRunResponse:
        message_text = self._coerce_messages(messages)
        resolved_team_id = self._resolve_team_id(team_id, metadata, context)

        async with ContextModulator.scope(resolved_team_id):
            try:
                brain_kwargs = self._build_brain_kwargs(message_text, kwargs, context=context)
                prediction = self._run_with_lm(brain_kwargs, resolved_team_id)
                decision = getattr(prediction, "decision", prediction)
                decision_payload = self._extract_payload(decision)

                pattern = getattr(decision, "pattern", None)
                target_team = getattr(decision, "target_team", None)
                if isinstance(decision_payload, dict):
                    pattern = pattern or decision_payload.get("pattern")
                    target_team = target_team or decision_payload.get("target_team")

                if pattern:
                    pattern = _normalize_route_pattern(str(pattern))
                pattern = pattern or "simple"
                target_team = target_team or "default"

                route_metadata = {
                    "route_pattern": pattern,
                    "target_team": target_team,
                    "original_task": message_text,
                }
                response_message = ChatMessage(
                    role=Role.ASSISTANT,
                    text=f"Routing to {pattern}",
                    additional_properties=route_metadata,
                )

                return AgentRunResponse(
                    messages=response_message,
                    value=decision_payload,
                    additional_properties=route_metadata,
                )
            except Exception as exc:  # pragma: no cover - defensive, used in prod
                error_message = ChatMessage(role=Role.SYSTEM, text=f"Error: {exc}")
                return AgentRunResponse(messages=error_message, value={"error": str(exc)})
