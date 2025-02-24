"""AgenticFleet Chainlit Application.

This module implements the Chainlit-based chat interface for AgenticFleet,
providing access to various AI agents for different tasks.
"""

import logging
from typing import Dict, Optional

import chainlit as cl

from agentic_fleet.core.agents.coding_agent import CodingAgent
from agentic_fleet.core.agents.mind_map_agent import MindMapAgent
from agentic_fleet.core.agents.web_search_agent import WebSearchAgent
from agentic_fleet.core.config.configuration_manager import ConfigurationManager

# Configure logging
logger = logging.getLogger(__name__)

# Initialize configuration
config = ConfigurationManager()

# Initialize agents with default configurations
agents: Dict[str, CodingAgent | MindMapAgent | WebSearchAgent] = {
    'coding': CodingAgent(
        name='coding_assistant',
        description='Helps with code generation and analysis',
        temperature=0.7
    ),
    'mind_map': MindMapAgent(
        name='mind_map_creator',
        description='Creates and manages knowledge graphs',
        temperature=0.5
    ),
    'web_search': WebSearchAgent(
        name='web_researcher',
        description='Performs web searches and information retrieval',
        temperature=0.6
    )
}


async def process_agent_message(agent_type: str, content: str) -> Optional[str]:
    """
    Process a message using the specified agent type.

    Args:
        agent_type: Type of agent to use ('coding', 'web_search', or 'mind_map')
        content: Message content to process

    Returns:
        Optional[str]: The agent's response, or None if processing failed
    """
    try:
        agent = agents[agent_type]
        logger.info(f"Processing message with {agent_type} agent")
        return await agent.process_message(content)
    except KeyError:
        logger.error(f"Invalid agent type: {agent_type}")
        return None
    except Exception as e:
        logger.error(f"Error processing message with {agent_type} agent: {str(e)}")
        return None


@cl.on_message
async def main(message: cl.Message) -> None:
    """
    Handle incoming messages and route to appropriate agent.

    Args:
        message: Incoming Chainlit message
    """
    try:
        # Create response object
        response = cl.Message(content="")

        # Route message based on content type
        content = message.content.lower()
        if 'code' in content:
            agent_response = await process_agent_message('coding', message.content)
        elif 'search' in content:
            agent_response = await process_agent_message('web_search', message.content)
        else:
            agent_response = await process_agent_message('mind_map', message.content)

        if agent_response:
            response.content = agent_response
            await response.send()
        else:
            await cl.Message(content="⚠️ Failed to process your request. Please try again.").send()

    except Exception as e:
        error_msg = f"Error processing message: {str(e)}"
        logger.error(error_msg)
        await cl.Message(content=f"⚠️ {error_msg}").send()


@cl.on_chat_start
async def start() -> None:
    """
    Initialize the chat session and display welcome message.
    Validates configuration and displays system status.
    """
    try:
        # Log initialization
        project_root = config.get_project_root()
        logger.info(f"Chat session started. Project root: {project_root}")
        # Send welcome message
        await cl.Message(
            content="Welcome to AgenticFleet! System initialized and ready to assist."
        ).send()
    except Exception as e:
        error_msg = f"Failed to initialize chat session: {str(e)}"
        logger.error(error_msg)
        await cl.Message(content=f"⚠️ {error_msg}").send()
        raise


@cl.on_message
async def main(message: cl.Message) -> None:
    """
    Handle incoming messages and route to appropriate agent.

    Args:
        message: Incoming Chainlit message
    """
    try:
        # Create response object
        response = cl.Message(content="")

        # Route message based on content type
        content = message.content.lower()
        if 'code' in content:
            agent_response = await process_agent_message('coding', message.content)
        elif 'search' in content:
            agent_response = await process_agent_message('web_search', message.content)
        else:
            agent_response = await process_agent_message('mind_map', message.content)

        if agent_response:
            response.content = agent_response
            await response.send()
        else:
            await cl.Message(content="⚠️ Failed to process your request. Please try again.").send()

    except Exception as e:
        error_msg = f"Error processing message: {str(e)}"
        logger.error(error_msg)
        await cl.Message(content=f"⚠️ {error_msg}").send()
        raise


@cl.on_chat_end
async def end() -> None:
    """
    Display goodbye message when the chat ends.
    """
    await cl.Message(content="Goodbye! Have a great day :)").send()


if __name__ == "__main__":
    cl.run()  # Starts the Chainlit server
