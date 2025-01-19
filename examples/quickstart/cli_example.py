"""
CLI example demonstrating basic AgenticFleet functionality.
"""

import asyncio
import logging
from typing import Optional

from agentic_fleet.models import (
    create_agent_team,
    EnhancedAssistantAgent,
    create_azure_client
)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def run_single_agent(prompt: str) -> None:
    """Demonstrate single agent usage."""
    try:
        # Create an agent
        agent = EnhancedAssistantAgent(
            name="cli_assistant",
            system_message="You are a helpful CLI assistant"
        )
        
        # Process message
        result = await agent.process_message(prompt)
        print(f"\nAgent response:\n{result}\n")
        
    except Exception as e:
        logger.error(f"Error in single agent: {str(e)}")

async def run_agent_team(task: str) -> None:
    """Demonstrate agent team usage."""
    try:
        # Create and configure team
        team = await create_agent_team(task)
        
        # Execute task
        result = await team.execute()
        print(f"\nTeam result:\n{result}\n")
        
    except Exception as e:
        logger.error(f"Error in agent team: {str(e)}")

async def main():
    """Run example scenarios."""
    # Single agent example
    await run_single_agent(
        "Write a Python function to calculate the factorial of a number"
    )
    
    # Agent team example
    await run_agent_team(
        """Create a data processing pipeline that:
        1. Reads CSV files
        2. Performs basic statistics
        3. Generates visualizations"""
    )

if __name__ == "__main__":
    asyncio.run(main())
