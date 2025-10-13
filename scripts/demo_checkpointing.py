#!/usr/bin/env python3
"""
Demo script showing workflow checkpointing capabilities.

This script demonstrates:
1. Creating a workflow with checkpointing enabled
2. Simulating a workflow that creates checkpoints
3. Listing available checkpoints
4. Restoring from a checkpoint
"""

import asyncio
import json
from pathlib import Path
from unittest.mock import AsyncMock, Mock, patch


async def demo_checkpointing():
    """Demonstrate checkpointing functionality."""
    print("=" * 70)
    print("AgenticFleet Workflow Checkpointing Demo")
    print("=" * 70)

    # Import after environment is set up
    from agenticfleet.config import settings
    from agenticfleet.workflows.multi_agent import MultiAgentWorkflow
    from agent_framework import FileCheckpointStorage

    # Create a temporary checkpoint storage
    checkpoint_dir = Path("./demo_checkpoints")
    checkpoint_dir.mkdir(exist_ok=True)
    checkpoint_storage = FileCheckpointStorage(str(checkpoint_dir))

    print(f"\n1. Creating workflow with checkpointing")
    print(f"   Storage: {checkpoint_dir}")

    # Mock the agents to avoid API calls
    with (
        patch("agenticfleet.workflows.multi_agent.create_orchestrator_agent"),
        patch("agenticfleet.workflows.multi_agent.create_researcher_agent"),
        patch("agenticfleet.workflows.multi_agent.create_coder_agent"),
        patch("agenticfleet.workflows.multi_agent.create_analyst_agent"),
        patch("agenticfleet.config.settings.settings") as mock_settings,
    ):

        mock_settings.workflow_config = {
            "workflow": {"max_rounds": 10, "max_stalls": 3}
        }

        workflow = MultiAgentWorkflow(checkpoint_storage=checkpoint_storage)
        workflow.set_workflow_id("demo_workflow")

        print("\n2. Simulating workflow execution with checkpoints")

        # Simulate workflow rounds
        for round_num in range(1, 4):
            workflow.current_round = round_num
            workflow.stall_count = 0
            workflow.last_response = f"Response from round {round_num}"
            workflow.context = {
                "user_query": "Demo task",
                "round": round_num,
                "progress": f"Completed step {round_num}",
            }

            checkpoint_id = await workflow.create_checkpoint(
                {"status": "in_progress", "step": f"Round {round_num}"}
            )
            print(f"   Round {round_num}: Created checkpoint {checkpoint_id[:8]}...")

        print("\n3. Listing all checkpoints")
        checkpoints = await workflow.list_checkpoints()
        print(f"   Found {len(checkpoints)} checkpoints:")
        for cp in checkpoints:
            print(f"   - {cp['checkpoint_id'][:8]}... (Round {cp['current_round']})")

        print("\n4. Restoring from checkpoint")
        if checkpoints:
            # Restore from the second checkpoint
            restore_id = checkpoints[1]["checkpoint_id"]
            print(f"   Restoring from checkpoint {restore_id[:8]}...")

            # Create new workflow instance and restore
            new_workflow = MultiAgentWorkflow(checkpoint_storage=checkpoint_storage)
            restored = await new_workflow.restore_from_checkpoint(restore_id)

            if restored:
                print(f"   ✓ Restored successfully!")
                print(f"   - Workflow ID: {new_workflow.workflow_id}")
                print(f"   - Current round: {new_workflow.current_round}")
                print(f"   - Last response: {new_workflow.last_response}")
                print(f"   - Context: {json.dumps(new_workflow.context, indent=6)}")
            else:
                print(f"   ✗ Restoration failed")

        print("\n5. Checkpoint file structure")
        checkpoint_files = list(checkpoint_dir.glob("*.json"))
        if checkpoint_files:
            print(f"   Examining {checkpoint_files[0].name}:")
            with open(checkpoint_files[0]) as f:
                data = json.load(f)
            print(f"   {json.dumps(data, indent=6)}")

        print("\n" + "=" * 70)
        print("Demo completed successfully!")
        print("=" * 70)

        # Cleanup
        print(f"\nCleaning up demo checkpoints in {checkpoint_dir}...")
        for file in checkpoint_dir.glob("*.json"):
            file.unlink()
        checkpoint_dir.rmdir()
        print("✓ Cleanup complete")


if __name__ == "__main__":
    asyncio.run(demo_checkpointing())
