# Standard library imports
import logging
import traceback
from pathlib import Path
from typing import Optional

# Third-party imports
import chainlit as cl
from autogen_ext.code_executors.local import LocalCommandLineCodeExecutor
from autogen_ext.teams.magentic_one import MagenticOne
from chainlit import Message, on_chat_start, on_message, on_settings_update, on_stop
from dotenv import load_dotenv

# Local imports - using the modular components
from agentic_fleet.config import config_manager
from agentic_fleet.core.application.manager import ApplicationConfig, ApplicationManager
from agentic_fleet.services.client_factory import get_cached_client
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


# Hook into chainlit events
@on_chat_start
async def start_chat(profile: cl.ChatProfile | None = None):
    """Initialize the chat session with the selected profile."""
    global client, app_manager

    try:
        # Initialize configuration
        config_manager.load_all()
        logger.info("Successfully loaded all configurations")

        # Validate environment
        if error := config_manager.validate_environment():
            raise ValueError(error)

        # Get environment settings
        env_config = config_manager.get_environment_settings()

        # Use the specified Azure OpenAI model
        model_name = "o4-mini"

        # Create cached client
        client = get_cached_client(model_name=model_name)

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

        # Initialize MagenticOne agent team
        team = MagenticOne(
            client=client,
            code_executor=LocalCommandLineCodeExecutor(),
            hil_mode=True  # Enable human-in-the-loop mode
        )

        # Store team in user session
        cl.user_session.set("agent_team", team)

        # Set up default settings
        default_settings = settings_manager.get_default_settings()
        cl.user_session.set("settings", default_settings)

        # Setup chat settings UI
        await settings_manager.setup_chat_settings()

        # Get profile information for welcome message
        profile_name = (
            profile.name if isinstance(profile, cl.ChatProfile) else "Default Profile"
        )
        profile_desc = (
            profile.markdown_description
            if isinstance(profile, cl.ChatProfile)
            else "Standard configuration"
        )

        # Send welcome message
        welcome_message = (
            f"🚀 Welcome to MagenticFleet!\n\n"
            f"**Active Profile**: {profile_name}\n"
            f"**Model**: {model_name}\n"
            f"**Temperature**: {default_settings['temperature']}\n"
            f"**Context Length**: 128,000 tokens\n\n"
            f"{profile_desc}"
        )

        await cl.Message(
            content=welcome_message,
            actions=[
                cl.Action(
                    name="reset_agents",
                    label="🔄 Reset Agents",
                    tooltip="Restart the agent team",
                    payload={"action": "reset"},
                )
            ],
        ).send()

    except Exception as e:
        error_msg = f"⚠️ Initialization failed: {str(e)}"
        logger.error(f"Chat start error: {traceback.format_exc()}")
        await cl.Message(content=error_msg).send()


@on_message
async def message_handler(message: cl.Message):
    """Handle incoming chat messages."""
    await handle_chat_message(message)


@on_settings_update
async def handle_settings_update(settings: cl.ChatSettings):
    """Handle updates to chat settings."""
    await settings_manager.handle_settings_update(settings)


@cl.action_callback("reset_agents")
async def on_action_reset(action: cl.Action):
    """Handle reset action."""
    await on_reset(action)


@on_stop
async def on_chat_stop():
    """Clean up resources when the chat is stopped."""
    global app_manager

    if app_manager:
        await app_manager.stop()
        logger.info("Application manager stopped")

    # Clear user session
    cl.user_session.clear()
