import pytest

from agentic_fleet.models import WorkflowSession
from agentic_fleet.services.chat_websocket import _event_generator


class _DummySessionManager:
    async def update_status(self, *args: object, **kwargs: object) -> None:
        """No-op session manager stub."""


class _DummyWorkflow:
    def __init__(self) -> None:
        self.last_task: str | None = None
        self.last_kwargs: dict[str, object] | None = None

    async def run_stream(self, task: str | None, **kwargs: object):
        self.last_task = task
        self.last_kwargs = dict(kwargs)
        if False:  # pragma: no cover
            yield None


@pytest.mark.asyncio
async def test_event_generator_does_not_forward_checkpoint_id_with_message():
    """agent-framework requires message XOR checkpoint_id; WS path must not forward checkpoint_id."""

    workflow = _DummyWorkflow()
    session_manager = _DummySessionManager()
    session = WorkflowSession(workflow_id="wf-test", task="hello")

    # Consume the generator to ensure `workflow.run_stream(...)` is invoked.
    _ = [
        event
        async for event in _event_generator(
            workflow,
            session,
            session_manager,
            checkpoint_id="cp-123",
            checkpoint_storage=object(),
        )
    ]

    assert workflow.last_task == "hello"
    assert workflow.last_kwargs is not None
    assert "checkpoint_id" not in workflow.last_kwargs
    assert "checkpoint_storage" in workflow.last_kwargs


@pytest.mark.asyncio
async def test_event_generator_forwards_checkpoint_id_on_resume():
    """Resume flow is task=None + checkpoint_id; generator must forward checkpoint_id."""

    workflow = _DummyWorkflow()
    session_manager = _DummySessionManager()
    session = WorkflowSession(workflow_id="wf-test", task="[resume]")

    _ = [
        event
        async for event in _event_generator(
            workflow,
            session,
            session_manager,
            task=None,
            checkpoint_id="cp-123",
            checkpoint_storage=object(),
        )
    ]

    assert workflow.last_task is None
    assert workflow.last_kwargs is not None
    assert workflow.last_kwargs.get("checkpoint_id") == "cp-123"
    assert "checkpoint_storage" in workflow.last_kwargs
