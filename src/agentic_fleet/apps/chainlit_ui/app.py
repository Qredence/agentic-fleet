"""Chainlit-based web interface for AutoGen agent interactions with MagenticOne."""

# Standard library imports
import base64
import io
import json
import logging
import os
import re
import time
import traceback
from typing import (
    Annotated,
    Any,
    AsyncGenerator,
    Dict,
    List,
    Literal,
    Optional,
    Tuple,
    TypeVar,
    Union,
)

# Third-party imports
import chainlit as cl
from autogen_agentchat.base import Response, TaskResult
from autogen_agentchat.conditions import TextMentionTermination
from autogen_agentchat.messages import (
    ChatMessage,
    ModelClientStreamingChunkEvent,
    MultiModalMessage,
    TextMessage,
)
from autogen_agentchat.ui import Console
from autogen_core import Image as AGImage
from autogen_ext.agents.file_surfer import FileSurfer
from autogen_ext.agents.magentic_one import MagenticOneCoderAgent
from autogen_ext.agents.web_surfer import MultimodalWebSurfer
from autogen_ext.code_executors.local import LocalCommandLineCodeExecutor
from autogen_ext.models.openai import AzureOpenAIChatCompletionClient
from autogen_ext.teams.magentic_one import MagenticOne
from chainlit import (
    Action,
    ChatProfile,
    Message,
    Task,
    TaskList,
    TaskStatus,
    Text,
    on_chat_start,
    on_message,
    on_settings_update,
    set_chat_profiles,
    user_session,
)
from dotenv import load_dotenv
from PIL import Image

# Local imports
from agentic_fleet.agent_registry import (
    initialize_agent_team,
)
from agentic_fleet.apps.chainlit_ui.agent_registry.default_agents import (
    initialize_default_agents,
)
from agentic_fleet.config import config_manager
from agentic_fleet.core.application.app_manager import ApplicationManager, Settings
from agentic_fleet.message_processing import (
    TASK_STATUS_COMPLETED,
    TASK_STATUS_FAILED,
    TASK_STATUS_RUNNING,
    process_response,
    stream_text,
)

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
            icon="/public/avatars/rocket.svg",
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
            icon="/public/avatars/microscope.svg",
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
    """Enhanced chat initialization with control panel"""
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
                    "model": "gpt-4o-mini",
                    "max_tokens": 128000,
                    "temperature_range": [0.3, 0.7],
                },
            )
            logger.info("Using default profile")
            user_session.set("chat_profile", profile)

        # Configure model based on profile name
        model_name = (
            "gpt-4o-mini"
            if isinstance(profile, cl.ChatProfile) and "Fast" in profile.name
            else "o3-mini"
        )

        # Initialize Azure OpenAI client with appropriate configuration
        client = AzureOpenAIChatCompletionClient(
            model=model_name,
            deployment=model_name,
            endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
            api_key=os.getenv("AZURE_OPENAI_API_KEY"),
            api_version=os.getenv("AZURE_OPENAI_API_VERSION"),
            streaming=True,
            model_info={
                "vision": False,  # Disable vision capabilities for now
                "function_calling": True,
                "json_output": True,
                "family": "azure",
                "architecture": model_name,
            },
        )

        # Initialize MagenticOne with configured client
        magentic_one = MagenticOne(
            client=client, hil_mode=True, code_executor=LocalCommandLineCodeExecutor()
        )

        # Store MagenticOne instance and profile in user session
        user_session.set("magentic_one", magentic_one)
        user_session.set("active_profile", profile)

        # Initialize application manager
        global app_manager
        app_manager = ApplicationManager(client)
        await app_manager.start()

        # Initialize default agents
        default_agents = initialize_default_agents(
            app_manager, config_manager, user_session, defaults, env_config
        )

        # Get team configuration
        team_config = config_manager.get_team_settings("magentic_fleet_one")

        # Initialize agent team
        agent_team = initialize_agent_team(
            app_manager, user_session, team_config, default_agents, defaults
        )
        user_session.set("agent_team", agent_team)

        # Store settings in user session
        model_configs = config_manager.get_model_settings("azure_openai")
        settings = Settings(model_configs=model_configs, fleet_config=team_config)
        user_session.set("settings", settings)

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
    """Enhanced message processing with step tracking"""
    try:
        # Handle both string and list content types
        if isinstance(message.content, str) and message.content.strip().lower() == "/reset":
            await on_reset(cl.Action(name="reset_agents", payload={"action": "reset"}))
            return

        team = user_session.get("magentic_one")
        if not team:
            raise ValueError("Agent team not initialized")

        # Create initial message to attach progress elements to
        initial_message = await cl.Message(
            content="🚀 Starting task processing..."
        ).send()

        # Store the initial message ID for all subsequent updates
        message_id = initial_message.id

        # Initialize task tracking with detailed descriptions
        task_ledger = cl.TaskList(
            status="🎯 Planning Tasks...",
            tasks=[
                cl.Task(
                    title=f"{icon} {agent}",
                    status=cl.TaskStatus.READY,
                    description=desc,
                )
                for agent, icon, desc in [
                    ("Orchestrator", "👑", "Plan and coordinate task execution"),
                    ("WebSurfer", "🌐", "Search and gather information from the web"),
                    ("FileSurfer", "📁", "Navigate and manage codebase files"),
                    ("Coder", "👨‍💻", "Write, review, and optimize code"),
                    ("Executor", "⚡", "Execute and validate commands"),
                ]
            ],
        )
        await task_ledger.send()

        # Initialize task status elements
        task_status = {
            "overview": cl.Text(
                name="task_overview",
                content="## 📋 Task Progress Overview\n\nMonitoring task execution and progress...\n",
                display="side",
            ),
            "planning": cl.Text(
                name="planned_tasks", content="### 📝 Planned Tasks\n", display="side"
            ),
            "execution": cl.Text(
                name="execution_progress",
                content="### ⚡ Execution Progress\n",
                display="side",
            ),
            "completion": cl.Text(
                name="completed_tasks",
                content="### ✅ Completed Tasks\n",
                display="side",
            ),
        }

        # Send initial status elements with message_id
        for element in task_status.values():
            await element.send(for_id=message_id)

        # Task planning phase
        await cl.Message(
            content="🎯 **Task Planning Phase**\n\nAnalyzing request and breaking down into subtasks...",
            author="System",
        ).send()

        async with cl.Step(name="Processing", type="workflow") as main_step:
            main_step.input = message.content
            current_phase = "planning"

            # Ensure task is a string
            task_content = message.content if isinstance(message.content, str) else str(message.content)
            async for event in team.run_stream(task=task_content):
                try:
                    # Event handling based on type
                    if isinstance(event, TextMessage):
                        # Detect task planning information
                        content = event.content
                        if current_phase == "planning" and any(
                            keyword in content.lower()
                            for keyword in [
                                "plan:",
                                "tasks:",
                                "steps:",
                                "will:",
                                "going to:",
                            ]
                        ):
                            # Extract and display task plan
                            await display_task_plan(content, task_status, message_id)
                            current_phase = "execution"
                            # Update overview
                            overview_element = cl.Text(
                                name="task_overview",
                                content=task_status["overview"].content
                                + "\n🔄 Transitioning to execution phase...\n",
                                display="side",
                            )
                            await overview_element.send(for_id=message_id)
                            task_status["overview"] = overview_element

                        # Format and send message with proper author
                        formatted_content = format_message_content(content)
                        await cl.Message(
                            content=formatted_content,
                            author=event.source or "Assistant",
                            language="json",
                        ).send()

                    elif hasattr(event, "tool_name"):
                        # Format tool calls with emoji and structure
                        tool_message = f"🔧 **Tool Call**: {event.tool_name}\n```json\n{json.loads(event.response)}\n```"
                        await cl.Message(
                            content=tool_message,
                            author="Tool Manager",
                            language="json",
                        ).send()

                        timestamp = time.strftime("%H:%M:%S")

                        # Update execution progress
                        execution_element = cl.Text(
                            name="execution_progress",
                            content=task_status["execution"].content
                            + f"\n[{timestamp}] {tool_message}\n",
                            display="side",
                        )
                        await execution_element.send(for_id=message_id)
                        task_status["execution"] = execution_element

                        # Update overview
                        overview_element = cl.Text(
                            name="task_overview",
                            content=task_status["overview"].content
                            + f"\n[{timestamp}] Using tool: {event.tool_name}\n",
                            display="side",
                        )
                        await overview_element.send(for_id=message_id)
                        task_status["overview"] = overview_element

                    elif isinstance(event, TaskResult):
                        await handle_task_completion(
                            event, task_ledger, task_status, message_id
                        )

                    # Update agent status in task ledger
                    if hasattr(event, "source"):
                        agent_type = event.source.split(".")[-1]
                        await update_agent_status(
                            agent_type, task_ledger, task_status, message_id
                        )

                except Exception as e:
                    await handle_processing_error(e)

            main_step.output = "Processing complete"
            # Final overview update
            timestamp = time.strftime("%H:%M:%S")
            overview_element = cl.Text(
                name="task_overview",
                content=task_status["overview"].content
                + f"\n[{timestamp}] ✨ Task processing completed\n",
                display="side",
            )
            await overview_element.send(for_id=message_id)
            task_status["overview"] = overview_element

    except Exception as e:
        await cl.Message(content=f"🚨 Critical error: {str(e)}").send()
        logger.error(f"Message processing failed: {traceback.format_exc()}")


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

    # Try different task list formats
    patterns = [
        r"(?:^|\n)(?:[-•*]|\d+\.)\s*(.+?)(?=(?:\n(?:[-•*]|\d+\.)|$))",  # Bullet points or numbered lists
        r"(?:^|\n)(?:Task|Step)\s*(?:\d+|[A-Z])[:\.]\s*(.+?)(?=\n|$)",  # Task/Step format
        r"(?:^|\n)I will\s*(.+?)(?=\n|$)",  # "I will" statements
        r"(?:^|\n)Going to\s*(.+?)(?=\n|$)",  # "Going to" statements
    ]

    for pattern in patterns:
        found_tasks = re.findall(pattern, content, re.MULTILINE)
        if found_tasks:
            tasks.extend(found_tasks)

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
    for task in task_ledger.tasks:
        task.status = cl.TaskStatus.DONE
    await task_ledger.update()

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
        language="json",
    ).send()


async def handle_processing_error(error: Exception):
    """Handle processing errors with proper formatting"""
    error_trace = traceback.format_exc()
    logger.error(f"Processing error: {error_trace}")
    await cl.Message(
        content=f"⚠️ **Error**\n```python\n{str(error)}\n```",
        author="System",
        language="json",
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
        task = task_ledger.tasks[idx]
        task.status = cl.TaskStatus.RUNNING
        await task_ledger.update()

        timestamp = time.strftime("%H:%M:%S")

        # Update execution progress
        execution_element = cl.Text(
            name="execution_progress",
            content=task_status["execution"].content
            + f"\n[{timestamp}] 🔄 **{task_type}**: {task.title} active\n",
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
    current_settings = user_session.get("settings", {})
    current_settings.update(new_settings)
    user_session.set("settings", current_settings)
    await cl.Message(content="⚙️ Settings updated", author="System").send()


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
    user_session.set("settings", settings)
    await cl.Message(content="⚙️ Chat settings initialized", author="System").send()


@cl.on_stop
async def cleanup():
    """Cleanup resources"""
    try:
        if magentic_one := user_session.get("magentic_one"):
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
        agent_team = user_session.get("agent_team")
        if not agent_team:
            await cl.Message(
                content="⚠️ No agent team available. Please reset the chat.",
                author="System",
            ).send()
            return

        # Get settings
        settings = user_session.get("settings", {})
        max_rounds = settings.get("max_rounds", DEFAULT_MAX_ROUNDS)
        max_time = settings.get("max_time", DEFAULT_MAX_TIME)

        # Create a list to collect responses
        collected_responses = []

        # Process the message through the agent team
        async with cl.Step(name="Processing Message", show_input=True) as step:
            step.input = message.content

            # Convert the message to a TextMessage for the agent team
            # Ensure content is a string
            content = message.content if isinstance(message.content, str) else str(message.content)
            agent_message = TextMessage(content=content, source="user")

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
