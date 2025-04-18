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
from dotenv import load_dotenv

# Local imports
from agentic_fleet.agents import create_magentic_one_agent
from agentic_fleet.config import config_manager
from agentic_fleet.config.llm_config_manager import llm_config_manager
from agentic_fleet.core.application.manager import ApplicationConfig, ApplicationManager

# Import MCP handlers to register them with Chainlit
# This import is used for its side effects (registering action callbacks)
# pylint: disable=unused-import
from agentic_fleet.mcp_pool import mcp_handlers  # noqa
from agentic_fleet.services.client_factory import create_client
from agentic_fleet.ui.message_handler import handle_chat_message, on_reset
from agentic_fleet.ui.settings_handler import SettingsManager

# Initialize logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

# Initialize application manager
app_manager: ApplicationManager | None = None

# Initialize settings manager
settings_manager = SettingsManager()

# Initialize client
client = None


# Chainlit event handlers
@on_chat_start
async def start_chat():
    """Initialize the chat session with the selected profile."""
    global client, app_manager

    # Get the selected chat profile
    profile = cl.user_session.get("chat_profile")
    profile_name = profile if isinstance(profile, str) else "default"
    logger.info(f"Selected chat profile: {profile_name}")

    # Get profile configuration from LLM config
    try:
        profile_config = llm_config_manager.get_profile_config(profile_name)
        profile_desc = profile_config.get("description", "Standard configuration")
        icon = profile_config.get("icon", "public/icons/rocket.svg")
        model_config = llm_config_manager.get_model_for_profile(profile_name)
        model_name = model_config.get("name", "gpt-4o-mini-2024-07-18")
    except ValueError as e:
        logger.warning(f"Error loading profile configuration: {e}")
        # Fallback to defaults
        profile_desc = "Standard configuration"
        icon = "public/icons/rocket.svg"
        model_name = "gpt-4o-mini-2024-07-18"

    # Store profile type in session
    cl.user_session.set("profile_type", profile_name)

    try:
        # Initialize configuration
        config_manager.load_all()
        logger.info("Successfully loaded all configurations")

        # Validate environment
        if error := config_manager.validate_environment():
            raise ValueError(error)

        # Get environment settings
        env_config = config_manager.get_environment_settings()

        # Use direct client creation to avoid the dict caching issues
        logger.info(f"Creating client for model {model_name}")
        client = create_client(
            model_name=model_name,
            streaming=True,
            vision=True,
            connection_pool_size=10,
            request_timeout=30,
        )

        # Initialize application manager
        app_manager = ApplicationManager(
            ApplicationConfig(
                project_root=Path(__file__).parent.parent,
                debug=env_config.get("debug", False),
                log_level=env_config.get("log_level", "INFO"),
            )
        )
        await app_manager.start()

        # Initialize task list
        from agentic_fleet.ui.task_manager import initialize_task_list
        await initialize_task_list()

        # Initialize agent based on profile
        team = await initialize_agent_for_profile(profile_name, client)
        profile_desc, icon = get_profile_metadata(profile_name)

        # Store team and profile info in user session
        cl.user_session.set("agent_team", team)
        cl.user_session.set("profile_icon", icon)

        # Set up default settings
        default_settings = settings_manager.get_default_settings()
        cl.user_session.set("settings", default_settings)

        # Setup chat settings UI
        await settings_manager.setup_chat_settings()

        # Send welcome message
        await send_welcome_message(profile_name, model_name, default_settings, profile_desc)

    except Exception as e:
        error_msg = f"⚠️ Initialization failed: {str(e)}"
        logger.error(f"Chat start error: {traceback.format_exc()}")
        await cl.Message(content=error_msg).send()


async def initialize_agent_for_profile(profile_name: str, client: object) -> object:
    """Initialize the appropriate agent based on the profile name.

    Args:
        profile_name: The name of the profile
        client: The LLM client to use

    Returns:
        The initialized agent team
    """
    try:
        # Get profile configuration
        profile_config = llm_config_manager.get_profile_config(profile_name)
        features = profile_config.get("features", {})

        # Get UI render mode from profile config
        ui_render_mode = profile_config.get("ui_render_mode", "tasklist")
        cl.user_session.set("ui_render_mode", ui_render_mode)

        # Initialize agent with features from config
        logger.info(f"Initializing agent for profile {profile_name}...")
        team = create_magentic_one_agent(
            client=client,
            hil_mode=features.get("hil_mode", True),
            mcp_enabled=features.get("mcp_enabled", False)
        )

        return team
    except ValueError:
        # Fallback to default initialization if profile not found
        logger.info("Initializing standard MagenticFleet agent configuration...")
        team = create_magentic_one_agent(
            client=client,
            hil_mode=True  # Enable human-in-the-loop mode
        )
        # Set tasklist UI render mode for standard profile
        cl.user_session.set("ui_render_mode", "tasklist")

        return team


def get_profile_metadata(profile_name: str) -> tuple[str, str]:
    """Get profile description and icon based on profile name.

    Args:
        profile_name: The name of the profile

    Returns:
        Tuple of (profile_description, icon_path)
    """
    try:
        # Get profile configuration
        profile_config = llm_config_manager.get_profile_config(profile_name)
        description = profile_config.get("description", "Standard AgenticFleet Profile")
        icon = profile_config.get("icon", "public/icons/rocket.svg")
        return description, icon
    except ValueError:
        # Fallback to defaults if profile not found
        if profile_name == "MCP Focus":
            return "MCP Interaction Profile", "public/icons/microscope.svg"
        return "Standard AgenticFleet Profile", "public/icons/rocket.svg"


async def send_welcome_message(profile_name: str, model_name: str, settings: dict[str, Any], profile_desc: str) -> None:
    """Send a welcome message with profile information.

    Args:
        profile_name: The name of the profile
        model_name: The name of the model
        settings: The settings dictionary
        profile_desc: The profile description
    """
    welcome_message = (
        f"🚀 Welcome to AgenticFleet!\n\n"
        f"**Active Profile**: {profile_name}\n"
        f"**Model**: {model_name}\n"
        f"**Temperature**: {settings['temperature']}\n\n"
        f"{profile_desc}"
    )

    # Create actions list
    actions = [
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
async def message_handler(message: cl.Message):
    """Handle incoming chat messages."""
    await handle_chat_message(message)


@on_settings_update
async def handle_settings_update(settings: dict[str, Any]):
    """Handle updates to chat settings."""
    await settings_manager.handle_settings_update(settings)


@cl.action_callback("reset_agents")
async def on_action_reset(action: cl.Action):
    """Handle reset action."""
    await on_reset(action)


@cl.action_callback("list_mcp_tools")
async def on_action_list_mcp(_: cl.Action):
    """Handle list MCP tools action."""
    try:
        # Import here to avoid circular imports
        from agentic_fleet.ui.components.mcp_panel import list_available_mcps

        # List available MCP configurations
        await list_available_mcps()
    except Exception as e:
        await cl.Message(
            content=f"Error retrieving MCP configurations: {str(e)}",
            author="System",
        ).send()
        logger.error(f"Error listing MCP configurations: {traceback.format_exc()}")


@on_stop
async def on_chat_stop():
    """Clean up resources when the chat is stopped."""
    global app_manager

    if app_manager:
        try:
            await app_manager.shutdown()
            logger.info("Application manager stopped")
        except Exception as e:
            logger.warning(f"Application manager cleanup error: {str(e)}")

    # Reset session values
    try:
        # Define keys to reset
        session_keys = [
            "agent_team", "settings", "current_task_list",
            "plan_steps", "plan_tasks", "profile_icon",
            "profile_type", "ui_render_mode"
        ]

        # Reset each key
        for key in session_keys:
            cl.user_session.set(key, None)

    except Exception as e:
        logger.warning(f"Session cleanup error: {str(e)}")


def main():
    """Run the Chainlit application."""
    import subprocess

    # Get configuration from environment variables
    host = os.environ.get("CHAINLIT_HOST", "0.0.0.0")
    port = int(os.environ.get("CHAINLIT_PORT", "8080"))

    # Log startup info
    logger.info(f"Starting Chainlit UI on {host}:{port}")

    # Get the current file path
    current_file = os.path.abspath(__file__)

    # Build chainlit command
    cmd = [
        "chainlit", "run",
        current_file,
        "--host", host,
        "--port", str(port),
        "--no-cache"
    ]

    logger.info(f"Executing: {' '.join(cmd)}")
    try:
        # Execute chainlit as a subprocess
        process = subprocess.run(cmd)
        sys.exit(process.returncode)
    except FileNotFoundError:
        logger.error("Chainlit command not found. Make sure it's installed correctly.")
        logger.error("Try running: ./scripts/setup_chainlit.sh")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Error running Chainlit: {e}")
        sys.exit(1)


# Make the module directly runnable
if __name__ == "__main__":
    main()
