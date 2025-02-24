# Standard library imports
import json
import logging
import os
import re
import time
import traceback
from abc import ABC
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

# Third-party imports
import chainlit as cl

# AutoGen imports
from autogen_agentchat.base import TaskResult
from autogen_agentchat.messages import (
    ChatMessage,
    MultiModalMessage,
    TextMessage,
)
from autogen_ext.code_executors.local import LocalCommandLineCodeExecutor
from autogen_ext.models.openai import AzureOpenAIChatCompletionClient
from autogen_ext.teams.magentic_one import MagenticOne
from chainlit import (
    Message,
    Step,
    Task,
    TaskList,
    TaskStatus,
    User,
    oauth_callback,
    on_chat_start,
    on_message,
    on_settings_update,
    on_stop,
    user_session,
)
from chainlit.chat_settings import ChatSettings
from chainlit.input_widget import Select, Slider, Switch
from dotenv import load_dotenv
from openai import AsyncAzureOpenAI
from pydantic import BaseModel, ConfigDict, Field
from typing_extensions import Annotated

# Local imports
from agentic_fleet.apps.chainlit_ui.agent_registry.default_agents import (
    initialize_agent_team,
    initialize_default_agents,
)
from agentic_fleet.config import config_manager
from agentic_fleet.core.application.manager import ApplicationConfig, ApplicationManager
from agentic_fleet.core.application.models import Settings
from agentic_fleet.message_processing import process_response

# Initialize logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

# Initialize configuration manager
try:
    config_manager.load_all()
    logger.info("Successfully loaded all configurations")

    # Validate environment
    if error := config_manager.validate_environment():
        raise ValueError(error)
except Exception as e:
    logger.error(f"Configuration error: {e}")
    raise

# Get environment settings
env_config = config_manager.get_environment_settings()

# Constants
STREAM_DELAY = env_config.get("stream_delay", 0.03)
PORT = int(os.getenv("CHAINLIT_PORT", os.getenv("PORT", "8000")))
HOST = os.getenv("CHAINLIT_HOST", os.getenv("HOST", "localhost"))

# Get default values
defaults = config_manager.get_defaults()
DEFAULT_MAX_ROUNDS = defaults.get("max_rounds", 10)
DEFAULT_MAX_TIME = defaults.get("max_time", 300)
DEFAULT_MAX_STALLS = defaults.get("max_stalls", 3)
DEFAULT_START_PAGE = defaults.get("start_page", "https://www.bing.com")
DEFAULT_TEMPERATURE = defaults.get("temperature", 0.7)
DEFAULT_SYSTEM_PROMPT = defaults.get("system_prompt", "")

app_manager: Optional[ApplicationManager] = None


# Factory function for client creation
def create_client(
    model_name: str,
    streaming: bool = True,
    vision: bool = False,
    connection_pool_size: int = 10,
    request_timeout: int = 30,
) -> AzureOpenAIChatCompletionClient:
    """Create and return an Azure OpenAI client with the specified configuration."""
    return AzureOpenAIChatCompletionClient(
        model=model_name,
        deployment=model_name,
        endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
        api_key=os.getenv("AZURE_OPENAI_API_KEY"),
        api_version=os.getenv("AZURE_OPENAI_API_VERSION"),
        model_streaming=streaming,
        model_info={
            "vision": vision,
            "function_calling": True,
            "json_output": True,
            "family": "gpt-4o" if "gpt-4o" in model_name else "azure",
            "architecture": model_name,
        },
        streaming=streaming,
        connection_pool_size=connection_pool_size,
        request_timeout=request_timeout,
    )


# Add connection pooling for Azure client
client = create_client(
    model_name="gpt-4o-mini-2024-07-18",
    streaming=True,
    vision=True,
    connection_pool_size=10,
    request_timeout=30,
)


# Add caching for config loading
@lru_cache(maxsize=1)
def load_cached_config():
    return config_manager.load_all()


@cl.set_chat_profiles
async def chat_profiles():
    """Define enhanced chat profiles with metadata and icons."""
    return [
        cl.ChatProfile(
            name="Magentic Fleet Fast",
            markdown_description=(
                "**Speed-Optimized Workflow**\n\n"
                "- Model: GPT-4o Mini (128k context)\n"
                "- Response Time: <2s average\n"
                "- Best for: Simple queries & quick tasks"
            ),
            icon="/public/icons/rocket.svg",
            metadata={
                "model": "gpt-4o-mini",
                "max_tokens": 128000,
                "temperature_range": [0.3, 0.7],
            },
        ),
        cl.ChatProfile(
            name="Magentic Fleet Max",
            markdown_description=(
                "**Advanced Reasoning Suite**\n\n"
                "- Model: O3 Mini (128k context)\n"
                "- Multi-agent collaboration\n"
                "- Complex problem solving"
            ),
            icon="/public/icons/microscope.svg",
            metadata={
                "model": "o3-mini",
                "max_tokens": 128000,
                "temperature_range": [0.5, 1.2],
            },
        ),
    ]


@cl.author_rename
def rename_author(orig_author: str) -> str:
    """Friendly agent names with emoji indicators"""
    rename_map = {
        "MagenticOne": "🤖 Magentic Assistant",
        "Orchestrator": "🎼 Orchestrator",
        "WebSurfer": "🌐 Web Navigator",
        "FileSurfer": "📁 File Explorer",
        "Coder": "👨‍💻 Code Architect",
        "Executor": "⚡ Action Runner",
        "System": "🛠️ System",
        "Tool Manager": "🔧 Tool Manager",
        "Assistant": "🤖 Assistant",
        "user": "👤 User",
        "Chatbot": "💬 Assistant",
    }
    # If the author is already prefixed with an emoji, return as is
    if orig_author and any(ord(c) > 0x1F00 for c in orig_author):
        return orig_author
    return rename_map.get(orig_author, f"🔹 {orig_author}")


@cl.action_callback("reset_agents")
async def on_reset(action: cl.Action):
    """Reset agent team with confirmation"""
    global app_manager
    if app_manager:
        await app_manager.shutdown()
    await on_chat_start()
    await cl.Message(content="🔄 Agents successfully reset!", author="System").send()


@cl.on_chat_start
async def on_chat_start():
    """Handle new chat session initialization."""
    app_user = cl.user_session.get("user")

    if app_user is None:
        # Use a default identifier for unauthenticated users
        identifier = "Guest"
    else:
        # Safely access the identifier with a fallback
        identifier = getattr(app_user, "identifier", "Guest")

    try:
        # Get the selected profile or create default
        profile = cl.user_session.get("chat_profile")

        # Create default profile if none selected or if profile is just a string
        if not profile or isinstance(profile, str):
            profile = cl.ChatProfile(
                name="Magentic Fleet Fast",
                markdown_description=(
                    "**Speed-Optimized Workflow**\n\n"
                    "- Model: GPT-4o Mini (128k context)\n"
                    "- Response Time: <2s average\n"
                    "- Best for: Simple queries & quick tasks"
                ),
                icon="/public/avatars/rocket.svg",
                metadata={
                    "model": "gpt-4o-mini-2024-07-18",
                    "max_tokens": 128000,
                    "temperature_range": [0.3, 0.7],
                },
            )
            logger.info("Using default profile")
            cl.user_session.set("chat_profile", profile)

        # Configure model based on profile name
        model_name = (
            "gpt-4o-mini-2024-07-18"
            if isinstance(profile, cl.ChatProfile) and "Fast" in profile.name
            else "o3-mini"
        )

        # Initialize Azure OpenAI client with appropriate configuration using factory
        client = create_client(
            model_name=model_name,
            streaming=True,
            vision=False,
        )

        # Initialize MagenticOne with configured client
        magentic_one = MagenticOne(
            client=client, hil_mode=True, code_executor=LocalCommandLineCodeExecutor()
        )

        # Store MagenticOne instance and profile in user session
        cl.user_session.set("magentic_one", magentic_one)
        cl.user_session.set("active_profile", profile)

        # Initialize application manager
        global app_manager
        app_manager = ApplicationManager(
            ApplicationConfig(
                project_root=Path(__file__).parent.parent,
                debug=env_config.get("debug", False),
                log_level=env_config.get("log_level", "INFO"),
            )
        )
        await app_manager.start()

        # Initialize default agents
        default_agents = initialize_default_agents(
            app_manager, config_manager, cl.user_session, defaults, env_config
        )

        # Get team configuration
        team_config = config_manager.get_team_settings("magentic_fleet_one")

        # Add environment validation before initialization
        required_env_vars = [
            "AZURE_OPENAI_ENDPOINT",
            "AZURE_OPENAI_API_KEY",
            "AZURE_OPENAI_API_VERSION",
        ]
        missing_vars = [var for var in required_env_vars if not os.getenv(var)]
        if missing_vars:
            raise ValueError(
                f"Missing required environment variables: {', '.join(missing_vars)}"
            )

        # Initialize agent team
        agent_team = await initialize_agent_team(
            app_manager, cl.user_session, team_config, default_agents, defaults
        )

        # Add team validation
        if not agent_team or not hasattr(agent_team, "run_stream"):
            raise RuntimeError("Agent team initialization failed - invalid team object")
        cl.user_session.set("agent_team", agent_team)

        # Store settings in user session
        settings = {
            "max_rounds": DEFAULT_MAX_ROUNDS,
            "max_time": DEFAULT_MAX_TIME,
            "max_stalls": DEFAULT_MAX_STALLS,
            "start_page": DEFAULT_START_PAGE,
            "temperature": DEFAULT_TEMPERATURE,
            "system_prompt": DEFAULT_SYSTEM_PROMPT,
        }
        cl.user_session.set("settings", settings)

        # Welcome message with profile details and reset control
        profile_name = (
            profile.name if isinstance(profile, cl.ChatProfile) else "Default Profile"
        )
        profile_desc = (
            profile.markdown_description
            if isinstance(profile, cl.ChatProfile)
            else "Standard configuration"
        )

        welcome_message = (
            f"🚀 Welcome to MagenticFleet!\n\n"
            f"**Active Profile**: {profile_name}\n"
            f"**Model**: {model_name}\n"
            f"**Temperature**: {DEFAULT_TEMPERATURE}\n"
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

        # Setup chat settings
        await setup_chat_settings()

    except Exception as e:
        error_msg = f"⚠️ Initialization failed: {str(e)}"
        logger.error(f"Chat start error: {traceback.format_exc()}")
        await cl.Message(content=error_msg).send()


@cl.on_message
async def on_message(message: cl.Message):
    """Process incoming messages with task tracking."""
    task_list = cl.TaskList()
    task_list.status = "Preparing agent team..."
    await task_list.send()

    try:
        # Task 1: Check for reset command
        reset_task = cl.Task(title="Checking command", status=cl.TaskStatus.RUNNING)
        await task_list.add_task(reset_task)
        reset_msg = await cl.Message(content="Checking command...").send()
        reset_task.forId = reset_msg.id

        if message.content.strip().lower() == "/reset":
            await on_reset(cl.Action(name="reset_agents", payload={"action": "reset"}))
            reset_task.status = cl.TaskStatus.DONE
            task_list.status = "Agents reset successfully"
            await task_list.send()
            return

        reset_task.status = cl.TaskStatus.DONE
        await task_list.send()

        # Task 2: Initialize agent team
        init_task = cl.Task(title="Initializing Agents", status=cl.TaskStatus.RUNNING)
        await task_list.add_task(init_task)
        init_msg = await cl.Message(content="Initializing agent team...").send()
        init_task.forId = init_msg.id

        team = cl.user_session.get("magentic_one")
        if not team:
            # Get settings from user session
            settings = cl.user_session.get("settings", {})
            team = MagenticOne(
                name="AgenticFleet Team",
                client=client,
                code_executor=LocalCommandLineCodeExecutor(),
            )
            cl.user_session.set("magentic_one", team)

        init_task.status = cl.TaskStatus.DONE
        await task_list.send()

        # Task 3: Process query
        process_task = cl.Task(title="Processing Query", status=cl.TaskStatus.RUNNING)
        await task_list.add_task(process_task)
        process_msg = await cl.Message(content="Processing your query...").send()
        process_task.forId = process_msg.id

        # Create a list to collect responses
        collected_responses = []
        
        # Create task message
        task_message = TextMessage(
            content=message.content,
            source="user",
        )
        
        # Process with MagenticOne's run_stream
        async with cl.Step(name="Processing with MagenticOne", show_input=True) as step:
            step.input = message.content
            
            # Stream responses from MagenticOne
            async for event in team.run_stream(task=message.content):
                # Process each event from the stream
                if hasattr(event, "content"):
                    await cl.Message(content=event.content, author=getattr(event, "author", "Agent")).send()
                    collected_responses.append(event.content)

        process_task.status = cl.TaskStatus.DONE
        await task_list.send()

        # Task 4: Format response
        format_task = cl.Task(title="Formatting Output", status=cl.TaskStatus.RUNNING)
        await task_list.add_task(format_task)
        
        if collected_responses:
            formatted_content = format_message_content("\n".join(collected_responses))
            result_msg = await cl.Message(
                content=formatted_content,
                author="Orchestrator",
                language="markdown"
            ).send()
            format_task.forId = result_msg.id

        format_task.status = cl.TaskStatus.DONE
        task_list.status = "Task completed successfully"
        await task_list.send()

    except Exception as e:
        error_task = cl.Task(title="Error Processing", status=cl.TaskStatus.FAILED)
        await task_list.add_task(error_task)
        task_list.status = f"Error: {str(e)}"
        await task_list.send()

        await cl.Message(
            content=f"Error: {str(e)}", author="System", language="text"
        ).send()
        logger.error(f"Message processing error: {traceback.format_exc()}")


def format_message_content(content: str) -> str:
    """Format message content with proper markdown and structure."""
    # Remove excessive newlines
    content = re.sub(r"\n{3,}", "\n\n", content.strip())

    # Format code blocks if present
    content = re.sub(
        r"```(\w+)?\n(.*?)\n```",
        lambda m: f"```{m.group(1) or ''}\n{m.group(2).strip()}\n```",
        content,
        flags=re.DOTALL,
    )

    # Add bullet points to lists
    content = re.sub(r"^(\d+\.\s)", "• ", content, flags=re.MULTILINE)

    return content


async def display_task_plan(
    content: str, task_status: Dict[str, cl.Text], message_id: str
):
    """Extract and display the task plan from agent's message"""
    # Extract tasks using regex patterns
    tasks = []
    for task in re.finditer(r"\d+\.\s+(.+?)(?=\n\d+\.|\n\n|$)", content):
        tasks.append(task.group(1).strip())

    if tasks:
        timestamp = time.strftime("%H:%M:%S")

        # Update planning section
        planning_element = cl.Text(
            name="planned_tasks",
            content=task_status["planning"].content
            + f"\n[{timestamp}] 📋 Task Breakdown:\n"
            + "\n".join(f"{i}. {task.strip()}" for i, task in enumerate(tasks, 1))
            + "\n",
            display="side",
        )
        await planning_element.send(for_id=message_id)
        task_status["planning"] = planning_element

        # Update overview
        overview_element = cl.Text(
            name="task_overview",
            content=task_status["overview"].content
            + f"\n[{timestamp}] 📝 Identified {len(tasks)} tasks to execute\n",
            display="side",
        )
        await overview_element.send(for_id=message_id)
        task_status["overview"] = overview_element


async def handle_task_completion(
    event: TaskResult,
    task_ledger: cl.TaskList,
    task_status: Dict[str, cl.Text],
    message_id: str,
):
    """Handle task completion events with proper formatting"""
    task_ledger.status = "✅ Task Completed"
    # Update all tasks to completed status
    for task in task_ledger.tasks:
        task.status = cl.TaskStatus.COMPLETED
    await task_ledger.send()

    result_content = event.content if hasattr(event, "content") else "Task completed"
    formatted_result = format_message_content(str(result_content))
    timestamp = time.strftime("%H:%M:%S")

    # Update completion status
    completion_element = cl.Text(
        name="completed_tasks",
        content=task_status["completion"].content
        + f"\n[{timestamp}] ✅ {formatted_result}\n",
        display="side",
    )
    await completion_element.send(for_id=message_id)
    task_status["completion"] = completion_element

    # Update overview
    overview_element = cl.Text(
        name="task_overview",
        content=task_status["overview"].content
        + f"\n[{timestamp}] ✅ Task completed: {formatted_result[:50]}{'...' if len(formatted_result) > 50 else ''}\n",
        display="side",
    )
    await overview_element.send(for_id=message_id)
    task_status["overview"] = overview_element

    await cl.Message(
        content=f"🎉 **Task Complete**\n\n{formatted_result}",
        author="System",
        language="markdown",
    ).send()


async def handle_processing_error(error: Exception):
    """Handle processing errors with proper formatting"""
    error_trace = traceback.format_exc()
    logger.error(f"Processing error: {error_trace}")
    await cl.Message(
        content=f"⚠️ **Error**\n```python\n{str(error)}\n```",
        author="System",
        language="markdown",
    ).send()


async def update_agent_status(
    agent_type: str,
    task_ledger: cl.TaskList,
    task_status: Dict[str, cl.Text],
    message_id: str,
):
    """Update agent status with proper formatting"""
    agent_map = {
        "WebSurfer": (1, "🌐 Web Search"),
        "FileSurfer": (2, "📁 File Operations"),
        "Coder": (3, "👨‍💻 Code Management"),
        "Executor": (4, "⚡ Command Execution"),
    }

    if agent_type in agent_map:
        idx, task_type = agent_map[agent_type]
        # Update task status
        if idx < len(task_ledger.tasks):
            task = task_ledger.tasks[idx]
            task.status = cl.TaskStatus.RUNNING
            await task_ledger.send()

        timestamp = time.strftime("%H:%M:%S")

        # Update execution progress
        execution_element = cl.Text(
            name="execution_progress",
            content=task_status["execution"].content
            + f"\n[{timestamp}] 🔄 **{task_type}**: Active\n",
            display="side",
        )
        await execution_element.send(for_id=message_id)
        task_status["execution"] = execution_element

        # Update overview
        overview_element = cl.Text(
            name="task_overview",
            content=task_status["overview"].content
            + f"\n[{timestamp}] 👉 {task_type} started\n",
            display="side",
        )
        await overview_element.send(for_id=message_id)
        task_status["overview"] = overview_element


# ========================
# SETTINGS & CLEANUP
# ========================


@cl.on_settings_update
async def update_settings(new_settings: Dict[str, Any]):
    """Update chat settings with new values."""
    current_settings = cl.user_session.get("settings", {})
    current_settings.update(new_settings)
    cl.user_session.set("settings", current_settings)
    await cl.Message(content="⚙️ Settings updated successfully", author="System").send()


async def setup_chat_settings():
    """Initialize chat settings with default values."""
    settings = {
        "max_rounds": DEFAULT_MAX_ROUNDS,
        "max_time": DEFAULT_MAX_TIME,
        "max_stalls": DEFAULT_MAX_STALLS,
        "start_page": DEFAULT_START_PAGE,
        "temperature": DEFAULT_TEMPERATURE,
        "system_prompt": DEFAULT_SYSTEM_PROMPT,
    }
    cl.user_session.set("settings", settings)
    await cl.Message(content="⚙️ Chat settings initialized successfully", author="System").send()


@cl.on_stop
async def cleanup():
    """Cleanup resources"""
    try:
        if magentic_one := cl.user_session.get("magentic_one"):
            await magentic_one.cleanup()
        if app_manager:
            await app_manager.shutdown()
    except Exception as e:
        logger.error(f"Cleanup error: {str(e)}")


def agent_input_widgets() -> list:
    """Generate Chainlit input widgets for agent configuration."""
    return [
        cl.Slider(
            id="temperature",
            label="Reasoning Temperature",
            min=0.0,
            max=2.0,
            step=0.1,
            value=DEFAULT_TEMPERATURE,
        ),
        cl.Select(
            id="reasoning_mode",
            label="Reasoning Strategy",
            values=["conservative", "balanced", "creative"],
            initial_value="balanced",
        ),
        cl.Switch(id="enable_validation", label="Auto-Validation", initial=True),
    ]


async def handle_message(message: cl.Message):
    """Handle incoming chat messages."""
    try:
        # Get the agent team from the session
        agent_team = cl.user_session.get("agent_team")
        if not agent_team:
            await cl.Message(
                content="⚠️ No agent team available. Please reset the chat.",
                author="System",
            ).send()
            return

        # Get settings
        settings = cl.user_session.get("settings", {})
        max_rounds = settings.get("max_rounds", DEFAULT_MAX_ROUNDS)
        max_time = settings.get("max_time", DEFAULT_MAX_TIME)

        # Create a list to collect responses
        collected_responses = []

        # Process the message through the agent team
        async with cl.Step(name="Processing Message", show_input=True) as step:
            step.input = message.content

            # Convert the message to a TextMessage for the agent team
            agent_message = TextMessage(content=message.content, source="user")

            # Process the message through each agent in the team
            for agent in agent_team:
                try:
                    response = await agent.process_message(agent_message)
                    await process_response(response, collected_responses)
                except Exception as e:
                    logger.error(
                        f"Error processing message with agent {agent.name}: {e}"
                    )
                    await cl.Message(
                        content=f"⚠️ Error with {agent.name}: {str(e)}", author="System"
                    ).send()

            step.output = "Message processed by agent team"

    except Exception as e:
        error_msg = f"⚠️ Error processing message: {str(e)}"
        logger.error(f"Message handling error: {traceback.format_exc()}")
        await cl.Message(content=error_msg, author="System").send()


async def run_team(
    agent_team: MagenticOne,
    task: str,
    task_ledger: Dict[str, Any],
    task_status: Dict[str, cl.Text],
    message_id: str,
):
    """Run the agent team on a task."""
    try:
        # Create task message
        task_message = TextMessage(
            content=task,
            source="user",
            metadata={"task_id": message_id},
        )

        # Stream team responses
        async for event in agent_team.run_stream(task_message):
            # Process each event from the stream
            if hasattr(event, "content"):
                author = getattr(event, "author", "Agent")
                content = event.content
                
                # Update task status based on agent type
                if hasattr(event, "agent_type"):
                    await update_agent_status(event.agent_type, task_ledger, task_status, message_id)
                
                # Send message to UI
                await cl.Message(content=content, author=author).send()
                
                # Check for task completion
                if hasattr(event, "is_complete") and event.is_complete:
                    await handle_task_completion(event, task_ledger, task_status, message_id)

    except Exception as e:
        logger.error(f"Error running agent team: {e}")
        await handle_processing_error(e)
