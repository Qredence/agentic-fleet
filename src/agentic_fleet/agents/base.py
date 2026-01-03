"""Base agent wrapper binding DSPy brains to the Agent Framework."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Optional, Type

import dspy
from agent_framework import (
    AgentRunResponse,
    AgentRunResponseUpdate,
    BaseAgent,
    ChatMessage,
    Role,
)

from agentic_fleet.dspy_modules.signatures import ExecutionResult, TaskContext
from agentic_fleet.llm import get_lm, resolve_model_alias
from agentic_fleet.middleware.context import ContextModulator


class FleetBrain(dspy.Module):
    """Wrapper that injects active team context and skills into DSPy calls."""

    def __init__(self, signature: Type[dspy.Signature]):
        super().__init__()
        self.signature = signature
        self.program = dspy.ChainOfThought(signature)

    def forward(self, **kwargs: Any) -> Any:
        ctx = ContextModulator.get_current()

        # Inject context if needed
        if "context" in self.signature.input_fields and "context" not in kwargs:
            if ctx is not None:
                kwargs["context"] = TaskContext(
                    team_id=ctx.team_id,
                    constraints=[],
                    tools=list(ctx.tools),
                    mounted_skills=list(ctx.mounted_skill_ids),
                    available_skills=list(ctx.available_skill_ids),
                )
            else:
                kwargs["context"] = TaskContext(
                    team_id="default",
                    constraints=[],
                    tools=[],
                    mounted_skills=[],
                    available_skills=[],
                )

        # Inject available_skills as comma-separated string if needed
        if "available_skills" in self.signature.input_fields and "available_skills" not in kwargs:
            if ctx is not None:
                kwargs["available_skills"] = ",".join(ctx.available_skill_ids)
            else:
                kwargs["available_skills"] = ""

        # Inject mounted_skills as comma-separated string if needed
        if "mounted_skills" in self.signature.input_fields and "mounted_skills" not in kwargs:
            if ctx is not None:
                kwargs["mounted_skills"] = ",".join(ctx.mounted_skill_ids)
            else:
                kwargs["mounted_skills"] = ""

        return self.program(**kwargs)


class BaseFleetAgent(BaseAgent):
    """Universal base agent that binds a DSPy brain to Agent Framework."""

    def __init__(
        self,
        name: str,
        role: str,
        brain_signature: Type[dspy.Signature],
        *,
        brain_state_path: str | None = None,
        model_role: str | None = None,
        model_alias: str | None = None,
        lm: dspy.BaseLM | None = None,
        **kwargs: Any,
    ):
        super().__init__(name=name, description=role, **kwargs)
        self.role = role
        self.model_role = model_role or role
        self.model_alias = model_alias
        self.lm_override = lm
        self.signature = brain_signature
        self.brain = FleetBrain(brain_signature)
        if brain_state_path:
            path = Path(brain_state_path)
            if path.exists():
                self.brain.program.load(str(path))

    async def run(
        self,
        messages: str | ChatMessage | list[str] | list[ChatMessage] | None = None,
        *,
        thread: Any | None = None,
        metadata: dict[str, Any] | None = None,
        context: Any | None = None,
        team_id: str | None = None,
        **kwargs: Any,
    ) -> AgentRunResponse:
        message_text = self._coerce_messages(messages)
        history = self._extract_history(messages, context)
        resolved_team_id = self._resolve_team_id(team_id, metadata, context)

        async with ContextModulator.scope(resolved_team_id):
            try:
                skills_to_mount = self._extract_skill_hints(history)
                if skills_to_mount:
                    ContextModulator.mount_multiple(skills_to_mount)
                brain_kwargs = self._build_brain_kwargs(message_text, kwargs, context=context, history=history)
                prediction = self._run_with_lm(brain_kwargs, resolved_team_id)
                payload = self._extract_payload(prediction)
                message_properties: dict[str, Any] = {}
                if isinstance(payload, dict):
                    if "required_skills" in payload:
                        message_properties["required_skills"] = payload["required_skills"]
                    if "mounted_skills" in payload:
                        message_properties["mounted_skills"] = payload["mounted_skills"]
                ctx = ContextModulator.get_current()
                if ctx is not None and ctx.mounted_skill_ids:
                    message_properties.setdefault("mounted_skills", list(ctx.mounted_skill_ids))
                response_message = ChatMessage(
                    role=Role.ASSISTANT,
                    text=str(payload),
                    additional_properties=message_properties or None,
                )
                additional_properties: dict[str, Any] = {}
                if ctx is not None:
                    additional_properties = {
                        "team_id": ctx.team_id,
                        "mounted_skills": list(ctx.mounted_skill_ids),
                        "available_skills": list(ctx.available_skill_ids),
                    }
                return AgentRunResponse(
                    messages=response_message,
                    value=payload,
                    additional_properties=additional_properties or None,
                )
            except Exception as exc:  # pragma: no cover - defensive, used in prod
                error_message = ChatMessage(role=Role.SYSTEM, text=f"Error: {exc}")
                return AgentRunResponse(messages=error_message, value={"error": str(exc)})

    def run_stream(
        self,
        messages: str | ChatMessage | list[str] | list[ChatMessage] | None = None,
        *,
        thread: Any | None = None,
        metadata: dict[str, Any] | None = None,
        context: Any | None = None,
        team_id: str | None = None,
        **kwargs: Any,
    ):
        async def _stream():
            response = await self.run(
                messages,
                thread=thread,
                metadata=metadata,
                context=context,
                team_id=team_id,
                **kwargs,
            )
            text = self._extract_text(response)
            yield AgentRunResponseUpdate(text=text, role=Role.ASSISTANT, response_id=response.response_id)

        return _stream()

    def _run_with_lm(self, brain_kwargs: dict[str, Any], team_id: str) -> Any:
        if self.lm_override is not None:
            with dspy.settings.context(lm=self.lm_override):
                return self.brain(**brain_kwargs)

        routing_enabled = os.getenv("FLEET_MODEL_ROUTING", "1") != "0"
        if routing_enabled:
            model_alias = self.model_alias or resolve_model_alias(self.model_role, team_id=team_id)
            lm = get_lm(model=model_alias)
            with dspy.settings.context(lm=lm):
                return self.brain(**brain_kwargs)

        return self.brain(**brain_kwargs)

    @staticmethod
    def _coerce_str_list(value: Any) -> list[str]:
        if value is None:
            return []
        if isinstance(value, list):
            return [str(item).strip() for item in value if str(item).strip()]
        if isinstance(value, str):
            return [item.strip() for item in value.split(",") if item.strip()]
        return []

    @classmethod
    def _extract_skill_hints(cls, history: list[Any]) -> list[str]:
        for item in reversed(history):
            props = None
            if isinstance(item, ChatMessage):
                props = item.additional_properties
            elif isinstance(item, dict):
                props = item.get("additional_properties", item)
            elif hasattr(item, "additional_properties"):
                props = getattr(item, "additional_properties")

            if isinstance(props, dict):
                for key in ("mounted_skills", "required_skills"):
                    if key in props:
                        return cls._coerce_str_list(props[key])
        return []

    def _resolve_team_id(
        self,
        team_id: str | None,
        metadata: dict[str, Any] | None,
        context: Any | None,
    ) -> str:
        resolved = team_id or "default"
        if metadata and "target_team" in metadata:
            resolved = str(metadata.get("target_team", resolved))
        elif context is not None and hasattr(context, "metadata"):
            resolved = str(getattr(context, "metadata", {}).get("target_team", resolved))
        else:
            active = ContextModulator.get_current()
            if active is not None:
                resolved = active.team_id
        return resolved

    def _build_brain_kwargs(
        self,
        message_text: str,
        extra_kwargs: dict[str, Any],
        *,
        context: Any | None = None,
        history: list[Any] | None = None,
    ) -> dict[str, Any]:
        input_fields = self.signature.input_fields
        brain_kwargs: dict[str, Any] = {}

        # Map the main message into the first relevant input field.
        for key in ("task", "step", "original_task", "message", "messages"):
            if key in input_fields:
                brain_kwargs[key] = message_text
                break
        else:
            if len(input_fields) == 1:
                only_key = next(iter(input_fields))
                brain_kwargs[only_key] = message_text

        if context is not None and "context" in input_fields and "context" not in brain_kwargs:
            brain_kwargs["context"] = context

        if history:
            if "worker_result" in input_fields and "worker_result" not in brain_kwargs:
                brain_kwargs["worker_result"] = self._extract_last_message_text(history)
            if "result" in input_fields and "result" not in brain_kwargs:
                brain_kwargs["result"] = self._coerce_execution_result(self._extract_last_message_text(history))
            if "original_task" in input_fields and "original_task" not in brain_kwargs:
                brain_kwargs["original_task"] = self._extract_first_message_text(history)

        for key in input_fields:
            if key not in brain_kwargs and key in extra_kwargs:
                brain_kwargs[key] = extra_kwargs[key]

        return brain_kwargs

    @staticmethod
    def _coerce_messages(messages: Any) -> str:
        if messages is None:
            return ""
        if isinstance(messages, str):
            return messages
        if isinstance(messages, ChatMessage):
            return messages.text or str(messages)
        if isinstance(messages, list):
            parts: list[str] = []
            for item in messages:
                if isinstance(item, str):
                    parts.append(item)
                elif isinstance(item, ChatMessage):
                    parts.append(item.text or str(item))
                else:
                    parts.append(str(item))
            return "\n".join([p for p in parts if p])
        return str(messages)

    @staticmethod
    def _extract_history(messages: Any, context: Any | None) -> list[Any]:
        if context is not None and hasattr(context, "history"):
            history = getattr(context, "history", None)
            if history is None:
                return []
            return list(history)
        if messages is None:
            return []
        if isinstance(messages, list):
            return messages
        return [messages]

    @staticmethod
    def _extract_first_message_text(history: list[Any]) -> str:
        for item in history:
            text = BaseFleetAgent._extract_message_text(item)
            if text:
                return text
        return ""

    @staticmethod
    def _extract_last_message_text(history: list[Any]) -> str:
        for item in reversed(history):
            text = BaseFleetAgent._extract_message_text(item)
            if text:
                return text
        return ""

    @staticmethod
    def _extract_message_text(item: Any) -> str:
        if isinstance(item, ChatMessage):
            return item.text or ""
        if isinstance(item, dict):
            return str(item.get("text") or item.get("content") or "")
        if hasattr(item, "message"):
            return BaseFleetAgent._extract_message_text(getattr(item, "message"))
        if hasattr(item, "messages"):
            messages = getattr(item, "messages")
            if isinstance(messages, list) and messages:
                return BaseFleetAgent._extract_message_text(messages[-1])
        if hasattr(item, "text"):
            return str(getattr(item, "text") or "")
        if hasattr(item, "content"):
            return str(getattr(item, "content") or "")
        return str(item) if item is not None else ""

    @staticmethod
    def _coerce_execution_result(raw: Any) -> Any:
        if isinstance(raw, ExecutionResult):
            return raw
        if isinstance(raw, dict):
            try:
                return ExecutionResult.model_validate(raw)
            except Exception:
                return raw
        if isinstance(raw, str):
            import ast
            import json

            for parser in (json.loads, ast.literal_eval):
                try:
                    parsed = parser(raw)
                except Exception:
                    continue
                if isinstance(parsed, dict):
                    try:
                        return ExecutionResult.model_validate(parsed)
                    except Exception:
                        return parsed
            return raw
        return raw

    @staticmethod
    def _extract_payload(prediction: Any) -> Any:
        for attr in ("content", "result", "decision"):
            if hasattr(prediction, attr):
                prediction = getattr(prediction, attr)
                break
        else:
            if hasattr(prediction, "__dict__"):
                # Try first output field if present
                for key in prediction.__dict__:
                    if not key.startswith("_"):
                        prediction = getattr(prediction, key)
                        break

        if hasattr(prediction, "model_dump"):
            return prediction.model_dump()
        if hasattr(prediction, "dict"):
            return prediction.dict()
        return prediction

    @staticmethod
    def _extract_text(response: AgentRunResponse) -> str:
        messages = response.messages
        if isinstance(messages, list) and messages:
            first = messages[0]
        else:
            first = messages
        if isinstance(first, ChatMessage):
            return first.text or str(first)
        return str(first) if first is not None else ""
