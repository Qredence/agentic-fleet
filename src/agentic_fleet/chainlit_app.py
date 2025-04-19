from dotenv import load_dotenv
load_dotenv()

import chainlit.cli

from agentic_fleet.ui.components.mcp_panel import (
    list_available_mcps,  # If circular import occurs, document reason below
)

"""
Chainlit application entry point for AgenticFleet.

This module serves as the primary entry point for the Chainlit UI application.
"""

# Standard library imports
import logging
import os
import sys
import traceback
from pathlib import Path
from typing import Any

# Third-party imports
import chainlit as cl
from chainlit import on_chat_start, on_message, on_settings_update, on_stop

# Local imports
from agentic_fleet.config import config_manager
from agentic_fleet.config.llm_config_manager import llm_config_manager
from agentic_fleet.core.agents.team import initialize_default_agents
from agentic_fleet.core.application.manager import ApplicationConfig, ApplicationManager
from agentic_fleet.services.client_factory import create_client
from agentic_fleet.ui.message_handler import handle_chat_message, on_reset
from agentic_fleet.ui.settings_handler import SettingsManager

# Import MCP handlers to register them with Chainlit
# This import is used for its side effects (registering action callbacks)
# pylint: disable=unused-import
try:
    import agentic_fleet.pool.mcp.mcp_handlers as mcp_handlers  # noqa
except ImportError:
    pass

# Initialize logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

# Context class to encapsulate app-wide state
class AppContext:
    def __init__(self) -> None:
        self.client: Any = None
        self.app_manager: ApplicationManager | None = None

app_context = AppContext()

# Initialize settings manager
settings_manager = SettingsManager()


# Chainlit event handlers
@on_chat_start
async def start_chat() -> None:
    """Initialize the chat session with the selected profile."""
    # Get the selected chat profile
    profile: str | None = cl.user_session.get("chat_profile")
    profile_name: str = profile if isinstance(profile, str) else "default"
    logger.info(f"Selected chat profile: {profile_name}")

    # Get profile configuration
    profile_config: dict[str, Any] = llm_config_manager.get_profile_config(profile_name)
    model_config: dict[str, Any] = profile_config.get("model_config", {})
    model_name: str = model_config.get("name", "o4-mini")
    profile_desc: str = profile_config.get("description", "Azure OpenAI o4-mini Model")
    icon: str = profile_config.get("icon", "public/icons/rocket.svg")

    # Store profile type in session
    cl.user_session.set("profile_type", profile_name)

    try:
        # Initialize configuration
        config_manager.load_all()
        logger.info("Successfully loaded all configurations")

        # Validate environment
        error: str | None = config_manager.validate_environment()
        if error:
            raise ValueError(error)

        # Get environment settings
        env_config: Any = config_manager.get_environment_settings()

        # Use profile-specific model_config for client creation
        logger.info(f"Creating client for model {model_name} with profile config")
        app_context.client = create_client(
            model_name=model_name,
            model_config=model_config,
            streaming=model_config.get("streaming", True),
            vision=model_config.get("vision", True),
            connection_pool_size=model_config.get("connection_pool_size", 10),
            request_timeout=model_config.get("request_timeout", 30),
        )

        # Initialize application manager
        app_context.app_manager = ApplicationManager(
            ApplicationConfig(
                project_root=Path(__file__).resolve().parent.parent,
                debug=getattr(env_config, "debug", False),
                log_level=getattr(env_config, "log_level", "INFO"),
            )
        )
        await app_context.app_manager.start()

        # Initialize task list
        from agentic_fleet.ui.task_manager import initialize_task_list

        await initialize_task_list()

        # Initialize agent based on profile
        agents = initialize_default_agents(model_client=app_context.client)
        team = agents[0] if agents else None
        profile_desc, icon = get_profile_metadata(profile_name)

        # Store team and profile info in user session
        cl.user_session.set("agent_team", team)
        cl.user_session.set("profile_icon", icon)

        # Set up default settings
        default_settings: dict[str, Any] = settings_manager.get_default_settings()
        cl.user_session.set("settings", default_settings)

        # Setup chat settings UI
        await settings_manager.setup_chat_settings()

        # Send welcome message
        await send_welcome_message(profile_name, model_name, default_settings, profile_desc)

    except Exception as e:
        error_msg: str = f"⚠️ Initialization failed: {str(e)}"
        logger.error(f"Chat start error: {traceback.format_exc()}")
        await cl.Message(content=error_msg).send()


def get_profile_metadata(profile_name: str) -> tuple[str, str]:
    """Get profile description and icon based on profile name.

    Args:
        profile_name: The name of the profile

    Returns:
        Tuple of (profile_description, icon_path)
    """
    try:
        # Get profile configuration
        profile_config: dict[str, Any] = llm_config_manager.get_profile_config(profile_name)
        description: str = profile_config.get("description", "Standard AgenticFleet Profile")
        icon: str = profile_config.get("icon", "public/icons/rocket.svg")
        return description, icon
    except ValueError:
        # Fallback to defaults if profile not found
        if profile_name == "MCP Focus":
            return "MCP Interaction Profile", "public/icons/microscope.svg"
        return "Standard AgenticFleet Profile", "public/icons/rocket.svg"


async def send_welcome_message(
    profile_name: str,
    model_name: str,
    settings: dict[str, Any],
    profile_desc: str
) -> None:
    """Send a welcome message with profile information.

    Args:
        profile_name: The name of the profile
        model_name: The name of the model
        settings: The settings dictionary
        profile_desc: The profile description
    """
    welcome_message: str = (
        f"🚀 Welcome to AgenticFleet!\n\n"
        f"**Active Profile**: {profile_name}\n"
        f"**Model**: {model_name}\n"
        f"**Temperature**: {settings['temperature']}\n\n"
        f"{profile_desc}"
    )

    # Create actions list
    actions: list[cl.Action] = [
        cl.Action(
            name="reset_agents",
            label="🔄 Reset Agents",
            tooltip="Restart the agent team",
            payload={"action": "reset"},
        )
    ]

    # Add MCP-specific action if profile is MCP Focus
    if profile_name == "MCP Focus":
        actions.append(
            cl.Action(
                name="list_mcp_tools",
                label="🛠️ List MCP Tools",
                tooltip="Show available MCP tools",
                payload={"action": "list_mcp"},
            )
        )

    await cl.Message(
        content=welcome_message,
        author=profile_name,
        actions=actions,
    ).send()


@on_message
async def message_handler(message: cl.Message) -> None:
    """Handle incoming chat messages."""
    await handle_chat_message(message)


@on_settings_update
async def handle_settings_update(settings: dict[str, Any]) -> None:
    """Handle updates to chat settings."""
    await settings_manager.handle_settings_update(settings)


@cl.action_callback("reset_agents")
async def on_action_reset(action: cl.Action) -> None:
    """Handle reset action."""
    await on_reset(action)


@cl.action_callback("list_mcp_tools")
async def on_action_list_mcp(_: cl.Action) -> None:
    """Handle list MCP tools action."""
    try:
        # List available MCP configurations
        await list_available_mcps()
    except Exception as e:
        await cl.Message(
            content=f"Error retrieving MCP configurations: {str(e)}",
            author="System",
        ).send()
        logger.error(f"Error listing MCP configurations: {traceback.format_exc()}")


@on_stop
async def on_chat_stop() -> None:
    """Clean up resources when the chat is stopped."""
    if app_context.app_manager:
        try:
            await app_context.app_manager.shutdown()
            logger.info("Application manager stopped")
        except Exception as e:
            logger.warning(f"Application manager cleanup error: {str(e)}")

    # Reset session values
    try:
        cl.user_session.clear()
    except Exception as e:
        logger.warning(f"Session cleanup error: {str(e)}")


def main() -> None:
    """Run the Chainlit application."""
    host: str = os.environ.get("CHAINLIT_HOST", "0.0.0.0")
    port_env: str = os.environ.get("CHAINLIT_PORT", "8080")
    try:
        port: int = int(port_env)
        if not (0 < port < 65536):
            port = 8080
    except Exception:
        port = 8080

    logger.info(f"Starting Chainlit UI on {host}:{port}")

    # Start Chainlit programmatically using the internal API
    # (Assuming internal API is chainlit.cli.run or similar)
    chainlit.cli.run(
        target=os.path.abspath(__file__),
        host=host,
        port=port,
        no_cache=True,
    )


# Make the module directly runnable
if __name__ == "__main__":
    main()