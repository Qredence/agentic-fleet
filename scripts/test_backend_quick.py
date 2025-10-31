"""Quick test script to verify REST-driven backend workflow execution.

To run this script, ensure that the 'src' directory is on your PYTHONPATH,
or install the package in editable mode from the project root:
    pip install -e .
Or run with:
    PYTHONPATH=src uv run python scripts/test_backend_quick.py
"""

from __future__ import annotations

import asyncio
from dataclasses import asdict
from agentic_fleet.api.conversations.service import get_store
from agentic_fleet.api.workflow_factory import WorkflowFactory
from agentic_fleet.api.workflows.service import WorkflowEvent, create_magentic_fleet_workflow


async def test_workflow_execution() -> None:
    """Exercise workflow factory, conversation store, and workflow stub."""

    print("=" * 60)
    print("Testing AgenticFleet REST backend")
    print("=" * 60)

    # 1. Test WorkflowFactory basics
    print("\n1. Loading workflow catalog...")
    factory = WorkflowFactory()
    workflows = factory.list_available_workflows()
    print(f"   ✅ Found {len(workflows)} workflow(s)")
    for workflow_summary in workflows:
        print(f"      - {workflow_summary['id']}: {workflow_summary['name']}")

    # 2. Inspect magentic_fleet configuration
    print("\n2. Inspecting magentic_fleet configuration...")
    config = factory.get_workflow_config("magentic_fleet")
    print(f"   ✅ Workflow name: {config.name}")
    print(f"   ✅ Factory function: {config.factory}")
    print(f"   ✅ Agent roles: {', '.join(config.agents.keys())}")

    # 3. Exercise workflow stub
    print("\n3. Running workflow stub...")
    workflow_instance = create_magentic_fleet_workflow()
    # Collected workflow events for quick verification
    collected: list[WorkflowEvent] = []
    async for event in workflow_instance.run("Quick test message"):
        collected.append(event)
    print(f"   ✅ Received {len(collected)} event(s): {collected}")

    # 4. Use conversation store
    print("\n4. Creating in-memory conversation...")
    store = get_store()
    conversation = store.create(title="Quickstart Conversation")
    store.add_message(conversation.id, "user", "Hello AgenticFleet!")
    store.add_message(conversation.id, "assistant", "Hello from workflow stub.")
    print(f"   ✅ Conversation stored: {asdict(conversation)}")

    print("\n" + "=" * 60)
    print("✅ Backend quick check complete!")
    print("=" * 60)
    print("\nNext steps:")
    print("  1. Start server: make backend")
    print("  2. Hit REST API: curl http://localhost:8000/v1/conversations")
    print("  3. Send chats: POST /v1/chat")


if __name__ == "__main__":
    asyncio.run(test_workflow_execution())
