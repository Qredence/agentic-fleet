"""Integration tests for Magentic workflow services."""

from __future__ import annotations

from collections.abc import AsyncGenerator
from typing import cast

import pytest

from agentic_fleet.api.workflow_factory import WorkflowFactory
from agentic_fleet.api.workflows.service import create_magentic_fleet_workflow


def test_workflow_factory_catalog() -> None:
    """WorkflowFactory exposes the magentic_fleet workflow definition."""

    factory = WorkflowFactory()
    workflows = factory.list_available_workflows()
    workflow_ids = {workflow["id"] for workflow in workflows}

    assert "magentic_fleet" in workflow_ids

    config = factory.get_workflow_config("magentic_fleet")
    assert config.factory == "create_magentic_fleet_workflow"
    assert set(config.agents.keys()) >= {"planner", "executor", "coder"}


@pytest.mark.asyncio
async def test_stub_workflow_emits_delta_and_done() -> None:
    """Stub workflow yields a delta event followed by a done event."""

    workflow = create_magentic_fleet_workflow()
    events = []
    stream = cast(AsyncGenerator[dict, None], workflow.run("Summarise AgenticFleet"))
    async for event in stream:
        events.append(event)

    assert events, "Expected at least one event"
    assert events[0]["type"] == "message.delta"
    assert events[-1]["type"] == "message.done"


def test_workflow_factory_missing_config() -> None:
    """WorkflowFactory raises ValueError for unknown workflow IDs."""

    factory = WorkflowFactory()
    with pytest.raises(ValueError):
        factory.get_workflow_config("unknown-workflow")
