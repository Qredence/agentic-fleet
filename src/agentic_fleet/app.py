"""Chainlit-based web interface for AutoGen agent interactions."""

# Standard library imports
import asyncio
import json
import logging
import os
import re
import time
from typing import Any, AsyncGenerator, Dict, List, Optional, Union

# Third-party imports
import chainlit as cl
import yaml

# AutoGen imports
from autogen_agentchat.agents import AssistantAgent, CodeExecutorAgent, UserProxyAgent
from autogen_agentchat.base import TaskResult
from autogen_agentchat.conditions import MaxMessageTermination, TextMentionTermination
from autogen_agentchat.messages import (
    AgentEvent,
    ChatMessage,
    FunctionCall,
    Image,
    MultiModalMessage,
    TextMessage,
)
from autogen_agentchat.teams import (
    MagenticOneGroupChat,
    SelectorGroupChat,
)
from autogen_agentchat.ui import Console
from autogen_ext.agents.file_surfer import FileSurfer
from autogen_ext.agents.magentic_one import MagenticOneCoderAgent
from autogen_ext.agents.web_surfer import MultimodalWebSurfer
from autogen_ext.code_executors.local import LocalCommandLineCodeExecutor
from autogen_ext.models.openai import AzureOpenAIChatCompletionClient
from chainlit import (
    Message,
    Step,
    Task,
    TaskList,
    TaskStatus,
    User,
    oauth_callback,
    on_message,
    on_settings_update,
    on_stop,
    user_session,
)
from chainlit.chat_settings import ChatSettings
from chainlit.input_widget import Select, Slider, Switch
from dotenv import load_dotenv

from agentic_fleet.backend.application_manager import ApplicationManager, Settings

# Initialize logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Load environment variables and verify required ones
load_dotenv()

# Verify required environment variables
required_env_vars = {
    "AZURE_OPENAI_API_KEY": os.getenv("AZURE_OPENAI_API_KEY"),
    "AZURE_OPENAI_ENDPOINT": os.getenv("AZURE_OPENAI_ENDPOINT"),
}

missing_env_vars = [name for name, value in required_env_vars.items() if not value]

if missing_env_vars:
    logger.error(
        f"Missing required environment variables: {', '.join(missing_env_vars)}"
    )
    raise ValueError(
        f"Missing required environment variables: {', '.join(missing_env_vars)}"
    )


# Constants
STREAM_DELAY = 0.01
PORT = int(os.getenv("PORT", "8001"))
HOST = os.getenv("HOST", "localhost")

# Default configuration values
DEFAULT_MAX_ROUNDS = 10
DEFAULT_MAX_TIME = 300  # 5 minutes
DEFAULT_MAX_STALLS = 3
DEFAULT_START_PAGE = "/welcome"


async def stream_text(text: str) -> AsyncGenerator[str, None]:
    """Stream text content word by word.

    Args:
        text: Text to stream

    Yields:
        Each word of the text with a delay
    """
    words = text.split()
    for i, word in enumerate(words):
        await asyncio.sleep(STREAM_DELAY)
        yield word + (" " if i < len(words) - 1 else "")


# OAuth configuration - only define callback if OAuth is enabled
if os.getenv("USE_OAUTH", "false").lower() == "true":

    @oauth_callback
    async def handle_oauth_callback(
        provider_id: str,
        token: str,
        raw_user_data: Dict[str, str],
        default_user: User,
    ) -> User:
        """Handle OAuth authentication callback using Supabase.

        Args:
            provider_id: OAuth provider identifier
            token: Authentication token
            raw_user_data: Raw user data from provider
            default_user: Default user object

        Returns:
            Updated user object
        """
        # Handle OAuth callback here
        return default_user


@on_settings_update
async def update_settings(new_settings: dict):
    try:
        # Get profile metadata if this is a profile change
        profile_metadata = new_settings.get("profile_metadata", {})
        if profile_metadata:
            # Apply profile settings
            temperature = float(profile_metadata.get("temperature", 0.7))
            max_rounds = int(profile_metadata.get("max_rounds", 10))
            max_time = int(profile_metadata.get("max_time", 300))
            system_prompt = profile_metadata.get(
                "system_prompt", "You are a helpful AI assistant."
            )
        else:
            # Apply manual settings
            temperature = float(new_settings.get("temperature", 0.7))
            max_rounds = int(new_settings.get("max_rounds", 10))
            max_time = int(new_settings.get("max_time", 300))
            system_prompt = new_settings.get(
                "system_prompt", "You are a helpful AI assistant."
            )

        # Update settings
        app_manager.settings.temperature = temperature
        app_manager.settings.max_rounds = max_rounds
        app_manager.settings.max_time = max_time
        app_manager.settings.system_prompt = system_prompt

        # Update session parameters
        user_session.set("max_rounds", max_rounds)
        user_session.set("max_time", max_time)

        # Send confirmation with applied settings
        settings_text = (
            f"Settings updated:\n"
            f"• Temperature: {temperature}\n"
            f"• Max Rounds: {max_rounds}\n"
            f"• Response Time: {max_time} seconds\n"
            f"• System Prompt: {system_prompt}"
        )
        await cl.Message(content=settings_text).send()

    except Exception as e:
        logger.error(f"Failed to update settings: {e}")
        await cl.Message(content=f"⚠️ Failed to update settings: {str(e)}").send()


# Define chat profiles with improved descriptions and settings
@cl.set_chat_profiles
async def chat_profiles():
    return [
        cl.ChatProfile(
            name="MagenticFleet One",
            markdown_description="""Balanced settings for general conversations.

• Temperature: 0.7 (Balanced creativity and consistency)
• Max Rounds: 10 (Standard conversation length)
• Response Time: 5 minutes (Quick responses)
• Features: Basic task handling and conversation""",
            icon="/public/icons/standard.png",
            default=True,
            metadata={
                "temperature": 0.7,
                "max_rounds": 10,
                "max_time": 300,
                "system_prompt": "You are a helpful AI assistant focused on balanced, clear communication.",
            },
        ),
        cl.ChatProfile(
            name="WebSearch Fleet",
            markdown_description="""Enhanced settings for complex tasks requiring deeper analysis.

• Temperature: 0.3 (Higher precision and consistency)
• Max Rounds: 20 (Extended analysis sessions)
• Response Time: 10 minutes (Thorough processing)
• Features: Complex problem-solving, code analysis, detailed explanations""",
            icon="/public/icons/advanced.png",
            metadata={
                "temperature": 0.3,
                "max_rounds": 20,
                "max_time": 600,
                "system_prompt": "You are an expert AI assistant focused on detailed analysis and precise solutions.",
            },
        ),
        cl.ChatProfile(
            name="Coding Fleet",
            markdown_description="""Optimized settings for creative tasks and brainstorming.

• Temperature: 1.0 (Maximum creativity)
• Max Rounds: 15 (Extended ideation sessions)
• Response Time: 7.5 minutes (Balanced processing)
• Features: Brainstorming, creative writing, idea generation""",
            icon="/public/icons/standard.png",
            metadata={
                "temperature": 1.0,
                "max_rounds": 15,
                "max_time": 450,
                "system_prompt": "You are a creative AI assistant focused on generating innovative ideas and solutions.",
            },
        ),
    ]


@cl.on_chat_start
async def start() -> None:
    """Initialize user session and set up agent team."""
    global app_manager

    try:
        logger.info("Loading application settings...")
        # Load model configuration from YAML file
        model_config_path = os.path.join(
            os.path.dirname(__file__), "backend", "models", "model_config.yaml"
        )
        try:
            with open(model_config_path, "r") as f:
                model_configs = yaml.safe_load(f)
        except FileNotFoundError:
            logger.error(f"Model configuration file not found: {model_config_path}")
            model_configs = {}
        except yaml.YAMLError as e:
            logger.error(f"Error parsing model configuration file: {e}")
            model_configs = {}

        # Load fleet configuration from YAML file
        fleet_config_path = os.path.join(
            os.path.dirname(__file__), "backend", "models", "fleet_config.yaml"
        )
        try:
            with open(fleet_config_path, "r") as f:
                fleet_config = yaml.safe_load(f)
        except FileNotFoundError:
            logger.error(f"Fleet configuration file not found: {fleet_config_path}")
            fleet_config = {}
        except yaml.YAMLError as e:
            logger.error(f"Error parsing fleet configuration file: {e}")
            fleet_config = {}

        # Initialize settings with loaded configurations
        settings = Settings(model_configs, fleet_config)

        # Store settings in session
        cl.user_session.set("settings", settings)

        logger.info(
            f"OAuth enabled: {settings.USE_OAUTH}, Providers: {settings.OAUTH_PROVIDERS}"
        )

        # Check OAuth configuration if enabled
        if settings.USE_OAUTH:
            oauth_error = check_oauth_configuration()
            if oauth_error:
                logger.error(f"OAuth configuration error: {oauth_error}")
                await Message(
                    content=f"⚠️ OAuth Configuration Error:\n{oauth_error}"
                ).send()
                settings.USE_OAUTH = False
                logger.info("OAuth has been disabled due to configuration errors")

        # Initialize model client
        model_client = AzureOpenAIChatCompletionClient(
            azure_deployment=settings.AZURE_OPENAI_DEPLOYMENT,
            model="o3-mini",  # Default to o3-mini
            azure_endpoint=settings.AZURE_OPENAI_ENDPOINT,
            api_key=settings.AZURE_OPENAI_API_KEY,
            api_version=settings.AZURE_OPENAI_API_VERSION,
            model_info={
                "name": "o3-mini",  # Default to o3-mini
                "context_length": 128000,
                "prompt_token_cost": 0.01,
                "completion_token_cost": 0.03,
                "vision": True,
                "function_calling": True,
                "json_output": True,
                "family": "azure",
                "architecture": "o3-mini",
            },
        )

        # Create and start application manager
        global app_manager
        app_manager = ApplicationManager(model_client)
        app_manager.settings = settings  # Set settings directly
        await app_manager.start()

        # Register cleanup handler
        app_manager.add_cleanup_handler(cleanup_workspace)

        # Initialize specialized agents with the model client from app_manager
        surfer = MultimodalWebSurfer(
            name="WebSurfer",
            model_client=app_manager.model_client,
            description="""You are an expert web surfer agent. Your role is to:
            1. Navigate and extract information from web pages
            2. Take screenshots of relevant content
            3. Summarize findings in a clear, structured format""",
            downloads_folder="./files/downloads",
            debug_dir="./files/debug",
            headless=True,
            start_page=user_session.get("start_page", DEFAULT_START_PAGE),
            animate_actions=False,
            to_save_screenshots=True,
            use_ocr=False,
            to_resize_viewport=True,
        )

        file_surfer = FileSurfer(
            name="FileSurfer",
            model_client=app_manager.model_client,
            description="""You are an expert file system navigator. Your role is to:
                1. Search and analyze files in the workspace
                2. Extract relevant information from files
                3. Organize and manage file operations efficiently""",
        )

        coder = MagenticOneCoderAgent(
            name="Coder", model_client=app_manager.model_client
        )

        # Create code executor with proper workspace
        workspace_dir = os.path.join(os.getcwd(), "./files/workspace")
        code_executor = LocalCommandLineCodeExecutor(
            work_dir=workspace_dir, timeout=300
        )

        # Create executor agent
        executor = CodeExecutorAgent(
            name="Executor",
            code_executor=code_executor,
            description="""You are an expert code execution agent. Your role is to:
                1. Safely execute code in the workspace
                2. Monitor execution and handle timeouts
                3. Provide detailed feedback on execution results
                4. Maintain a clean and organized workspace""",
        )

        # Get active chat profile
        active_profile = user_session.get("active_chat_profile", "MagenticFleet One")
        
        # Initialize team based on active profile
        if active_profile == "MagenticFleet One":
            team = MagenticOneGroupChat(
                model_client=model_client,
                participants=[surfer, file_surfer, coder, executor],
                max_turns=user_session.get("max_rounds", DEFAULT_MAX_ROUNDS),
                max_stalls=user_session.get("max_stalls", DEFAULT_MAX_STALLS),
            )
        elif active_profile == "WebSearch Fleet":
            team = SelectorGroupChat(
                agents=[surfer, file_surfer],
                model_client=model_client,
                termination_conditions=[
                    MaxMessageTermination(max_messages=user_session.get("max_rounds", DEFAULT_MAX_ROUNDS)),
                    TextMentionTermination(text="DONE", ignore_case=True)
                ],
                selector_description="Select the most appropriate agent to handle the current task step."
            )
        elif active_profile == "Coding Fleet":
            team = SelectorGroupChat(
                agents=[file_surfer, coder, executor],
                model_client=model_client,
                termination_conditions=[
                    MaxMessageTermination(max_messages=user_session.get("max_rounds", DEFAULT_MAX_ROUNDS)),
                    TextMentionTermination(text="DONE", ignore_case=True)
                ],
                selector_description="Select the most appropriate agent for code-related tasks."
            )
        else:
            # Default to MagenticFleet One if profile not recognized
            team = MagenticOneGroupChat(
                model_client=model_client,
                participants=[surfer, file_surfer, coder, executor],
                max_turns=user_session.get("max_rounds", DEFAULT_MAX_ROUNDS),
                max_stalls=user_session.get("max_stalls", DEFAULT_MAX_STALLS),
            )
        user_session.set("team", team)

        # Initialize task list
        task_list = TaskList()
        task_list.status = "Ready"
        user_session.set("task_list", task_list)
        await task_list.send()

        await Message(
            content="✅ Your multi-agent team is ready! Each agent has been initialized with specialized capabilities."
        ).send()

        # Display welcome message and settings
        app_user = user_session.get("user")
        greeting = (
            f"Hi {app_user.identifier}! 👋"
            if app_user
            else "Hi there! Welcome to AgenticFleet 👋"
        )
        await Message(
            content=f"{greeting} Feel free to adjust your experience in the settings above."
        ).send()

        # Initialize and send chat settings
        chat_settings = ChatSettings()
        await chat_settings.send()

        # Initialize session parameters
        user_session.set("max_rounds", DEFAULT_MAX_ROUNDS)
        user_session.set("max_time", DEFAULT_MAX_TIME)
        user_session.set("max_stalls", DEFAULT_MAX_STALLS)
        user_session.set("start_page", DEFAULT_START_PAGE)

        # Display settings summary
        welcome_text = (
            "Here's your setup (easily adjustable in settings):\n\n"
            f"• Rounds: {DEFAULT_MAX_ROUNDS} conversations\n"
            f"• Time: {DEFAULT_MAX_TIME} min\n"
            f"• Stalls: {DEFAULT_MAX_STALLS} before replanning\n"
            f"• Start URL: {DEFAULT_START_PAGE}"
        )
        await Message(content=welcome_text).send()

        # Create necessary directories
        for directory in [
            "./files/workspace",
            "./files/debug",
            "./files/downloads",
            "./files",
        ]:
            os.makedirs(os.path.join(os.getcwd(), directory), exist_ok=True)

    except Exception as e:
        logger.error(f"Failed to initialize session: {str(e)}")
        await Message(content=f"⚠️ Session initialization failed: {str(e)}").send()
        raise


@cl.step(name="Response Processing", type="process", show_input=True)
async def process_response(
    response: Union[TaskResult, TextMessage, List[Any], Dict[str, Any]],
    collected_responses: List[str],
) -> None:
    """Process agent responses with step visualization and error handling."""
    try:
        current_step = cl.context.current_step
        current_step.input = str(response)

        if isinstance(response, TaskResult):
            async with cl.Step(
                name="Task Execution",
                type="task",
                show_input=True,
                language="json"
            ) as task_step:
                task_step.input = getattr(response, "task", "Task execution")

                for msg in response.messages:
                    await process_message(msg, collected_responses)

                if response.stop_reason:
                    task_step.output = f"Task stopped: {response.stop_reason}"
                    task_step.is_error = True
                    await Message(
                        content=f"🛑 {task_step.output}", author="System"
                    ).send()

        elif isinstance(response, TextMessage):
            source = getattr(response, "source", "Unknown")
            async with cl.Step(
                name=f"Agent: {source}",
                type="message",
                show_input=True
            ) as msg_step:
                msg_step.input = response.content
                await process_message(response, collected_responses)
                msg_step.output = f"Message from {source} processed"

        elif hasattr(response, "chat_message"):
            async with cl.Step(
                name="Chat Message",
                type="message",
                show_input=True
            ) as chat_step:
                chat_step.input = str(response.chat_message)
                await process_message(response.chat_message, collected_responses)
                chat_step.output = "Chat message processed"

        elif hasattr(response, "inner_monologue"):
            async with cl.Step(
                name="Inner Thought",
                type="reasoning",
                show_input=True
            ) as thought_step:
                thought_step.input = str(response.inner_monologue)
                await process_message(response.inner_monologue, collected_responses)
                thought_step.output = "Inner thought processed"

        elif hasattr(response, "function_call"):
            async with cl.Step(
                name="Function Call",
                type="function",
                show_input=True,
                language="json"
            ) as func_step:
                func_step.input = str(response.function_call)
                collected_responses.append(str(response.function_call))
                func_step.output = "Function call processed"

        elif isinstance(response, (list, tuple)):
            for item in response:
                await process_response(item, collected_responses)

        else:
            collected_responses.append(str(response))
            current_step.output = "Unknown response type processed"

    except Exception as e:
        logger.error(f"Error processing response: {str(e)}")
        await Message(content=f"⚠️ Error processing response: {str(e)}").send()


@cl.step(name="Message Processing", type="message", show_input=True)
async def process_message(
    message: Union[TextMessage, Any], collected_responses: List[str]
) -> None:
    """Process a single message with proper formatting and step visualization.

    Args:
        message: Message to process
        collected_responses: List to collect processed responses
    """
    try:
        current_step = cl.context.current_step
        # Extract content and source
        content = message.content if hasattr(message, "content") else str(message)
        source = getattr(message, "source", "Unknown")
        current_step.input = content

        # Check for plan and update task list
        steps = extract_steps_from_content(content)
        if steps:
            async with cl.Step(
                name="Plan Creation",
                type="planning",
                show_input=True,
                language="markdown"
            ) as plan_step:
                plan_step.input = content
                task_list = user_session.get("task_list")
                if task_list:
                    task_list.tasks.clear()  # Clear existing tasks
                    task_list.status = "Creating tasks..."
                    await task_list.send()

                    # Add tasks with delays for visual feedback
                    for step in steps:
                        task = cl.Task(title=step)
                        await task_list.add_task(task)
                        await cl.sleep(0.2)  # Small delay between tasks

                    task_list.status = "Ready to execute..."
                    await task_list.send()
                    plan_step.output = f"Created plan with {len(steps)} steps"

        # Format content based on message type
        if isinstance(message, TextMessage):
            # Send the message with proper attribution
            step_name = f"Message from {source}"
            async with Step(name=step_name, type="message") as msg_step:
                msg_step.input = content
                # Stream text content using Chainlit's streaming capability
                msg = Message(content="", author=source)
                async for chunk in stream_text(content):
                    await msg.stream_token(chunk)
                await msg.send()
                collected_responses.append(content)
                msg_step.output = "Message processed"

        elif isinstance(message, MultiModalMessage):
            # Process multimodal content
            async with Step(name="Multimodal Processing", type="media") as media_step:
                media_step.input = "Processing multimodal message"
                for item in message.content:
                    if isinstance(item, Image):
                        image_data = getattr(item, "data", None) or getattr(
                            item, "content", None
                        )
                        if image_data:
                            await _handle_image_data(image_data)
                media_step.output = "Multimodal content processed"

        elif isinstance(message, FunctionCall):
            # Handle function calls
            async with Step(
                name=f"Function: {message.name}", type="function"
            ) as func_step:
                func_step.input = json.dumps(message.args, indent=2)
                await Message(
                    content=f"🛠️ Function: {message.name}\nArgs: {json.dumps(message.args, indent=2)}",
                    author=source,
                    indent=1,
                ).send()
                func_step.output = "Function call processed"
        else:
            # Handle other message types
            async with Step(name="Generic Message", type="other") as gen_step:
                gen_step.input = content
                # Stream text content using Chainlit's streaming capability
                msg = Message(content="", author="System")
                async for chunk in stream_text(content):
                    await msg.stream_token(chunk)
                await msg.send()
                collected_responses.append(content)
                gen_step.output = "Message processed"

    except Exception as e:
        logger.error(f"Error processing message: {str(e)}")
        await Message(content=f"⚠️ Error processing message: {str(e)}").send()


def extract_steps_from_content(content: str) -> List[str]:
    """Extract steps from the content.

    Args:
        content: Content string to extract steps from

    Returns:
        List of extracted steps
    """
    steps = []
    if "Here is the plan to follow as best as possible:" in content:
        plan_section = content.split("Here is the plan to follow as best as possible:")[
            1
        ].strip()
        # Split by bullet points and filter out empty lines
        for line in plan_section.split("\n"):
            line = line.strip()
            if line.startswith(("- ", "* ")):
                # Remove the bullet point and clean up
                step = line[2:].strip()
                if step:
                    # Remove markdown formatting and extra whitespace
                    step = re.sub(r"\*\*|\`\`\`|\*", "", step)
                    step = re.sub(r"\s+", " ", step)
                    steps.append(step)
    return steps


async def _process_multimodal_message(content: List[Any]) -> None:
    """Process a multimodal message containing text and images.

    Args:
        content: List of message content items
    """
    try:
        for item in content:
            if isinstance(item, Image):
                # Handle image data - check for both data and content attributes
                image_data = getattr(item, "data", None) or getattr(
                    item, "content", None
                )
                if image_data:
                    await _handle_image_data(image_data)

    except Exception as e:
        logger.error(f"Error processing multimodal message: {str(e)}")
        await Message(content=f"⚠️ Error processing multimodal message: {str(e)}").send()


async def _handle_image_data(image_data: Union[str, bytes]) -> Optional[Image]:
    """Handle image data processing and display.

    Args:
        image_data: Image data as string or bytes
    """
    try:
        if isinstance(image_data, str):
            if image_data.startswith(("http://", "https://")):
                # Display remote images directly
                image = Image(url=image_data, display="inline")
                await Message(content="📸 New screenshot:", elements=[image]).send()
                return image
            elif os.path.isfile(image_data):
                # Display local images
                image = Image(path=image_data, display="inline")
                await Message(content="📸 New screenshot:", elements=[image]).send()
                return image
        elif isinstance(image_data, bytes):
            # Save and display bytes data
            logs_dir = os.path.join(os.getcwd(), "logs")
            debug_dir = os.path.join(logs_dir, "debug")
            os.makedirs(debug_dir, exist_ok=True)
            temp_path = os.path.join(debug_dir, f"screenshot_{int(time.time())}.png")
            with open(temp_path, "wb") as f:
                f.write(image_data)
            image = Image(path=temp_path, display="inline")
            await Message(content="📸 New screenshot:", elements=[image]).send()
            return image

    except Exception as e:
        logger.error(f"Error handling image data: {str(e)}")
        await Message(content=f"⚠️ Error handling image: {str(e)}").send()

    return None


@on_message
async def handle_message(message: Message):
    """Handle incoming user messages and coordinate agent responses with step visualization."""
    try:
        async with cl.Step(name="Message Handler", type="handler", show_input=True) as current_step:
            current_step.input = message.content

            # Get task list and team from session
            task_list = user_session.get("task_list")
            team = user_session.get("team")

            if not task_list or not team:
                current_step.is_error = True
                current_step.output = "Session not initialized"
                await Message(
                    content="⚠️ Session not initialized. Please refresh the page."
                ).send()
                return

            # Reset task list for new message
            task_list = TaskList()
            task_list.status = "Planning..."
            await task_list.send()
            user_session.set("task_list", task_list)

            # Process message with team
            collected_responses = []
            current_task = None

            async with cl.Step(
                name="Team Processing",
                type="team",
                show_input=True
            ) as team_step:
                team_step.input = message.content
                
                async for response in team.run_stream(task=message.content):
                    # Process the response
                    await process_response(response, collected_responses)

                    # Update task status if we have tasks
                    if task_list.tasks:
                        # Find first non-completed task
                        for task in task_list.tasks:
                            if task.status != TaskStatus.DONE:
                                task.status = TaskStatus.RUNNING
                                current_task = task
                                break
                        await task_list.send()

                    # Mark current task as done if we have one
                    if current_task:
                        current_task.status = TaskStatus.DONE
                        current_task = None
                        await task_list.send()

                # Mark all remaining tasks as done
                for task in task_list.tasks:
                    if task.status != TaskStatus.DONE:
                        task.status = TaskStatus.DONE
                task_list.status = "Done"
                await task_list.send()

                team_step.output = f"Team processed message with {len(collected_responses)} responses"

            current_step.output = "Message handled successfully"

    except Exception as e:
        logger.error(f"Error processing message: {str(e)}")
        if task_list:
            task_list.status = "Failed"
            await task_list.send()
        await Message(content=f"⚠️ Error processing message: {str(e)}").send()


@on_stop
async def cleanup() -> None:
    """Clean up resources when the application stops."""
    try:
        # Get the team from session
        team = user_session.get("team")
        if team:
            # Clean up team resources
            await team.cleanup()

        # Mark any running tasks as failed
        task_list = user_session.get("task_list")
        if task_list:
            for task in task_list.tasks:
                if task.status == cl.TaskStatus.RUNNING:
                    task.status = cl.TaskStatus.FAILED
            task_list.status = "Stopped"
            await task_list.send()

        # Clean up workspace
        workspace_dir = os.path.join(os.getcwd(), "workspace")
        if os.path.exists(workspace_dir):
            import shutil

            shutil.rmtree(workspace_dir)

    except Exception as e:
        logger.exception("Cleanup failed")
        await Message(content=f"⚠️ Cleanup error: {str(e)}").send()


def check_oauth_configuration() -> Optional[str]:
    """Check OAuth configuration and return an error message if misconfigured.

    Returns:
        Optional[str]: Error message if configuration is invalid, None otherwise
    """
    try:
        required_vars = {
            "OAUTH_GITHUB_CLIENT_ID": os.getenv("OAUTH_GITHUB_CLIENT_ID"),
            "OAUTH_GITHUB_CLIENT_SECRET": os.getenv("OAUTH_GITHUB_CLIENT_SECRET"),
            "OAUTH_GOOGLE_CLIENT_ID": os.getenv("OAUTH_GOOGLE_CLIENT_ID"),
            "OAUTH_GOOGLE_CLIENT_SECRET": os.getenv("OAUTH_GOOGLE_CLIENT_SECRET"),
            "OAUTH_REDIRECT_URI": os.getenv("OAUTH_REDIRECT_URI"),
        }

        missing_vars = [var for var, value in required_vars.items() if not value]

        if missing_vars:
            return f"Missing required OAuth environment variables: {', '.join(missing_vars)}"

        providers = os.getenv("OAUTH_PROVIDERS", "").split(",")
        if not providers or not any(providers):
            return "No OAuth providers configured in OAUTH_PROVIDERS"

        return None

    except Exception as e:
        logger.error(f"Error checking OAuth configuration: {str(e)}")
        return f"Failed to check OAuth configuration: {str(e)}"


async def cleanup_workspace() -> None:
    """Clean up the workspace directory."""
    try:
        workspace_dir = os.path.join(os.getcwd(), "workspace")
        if os.path.exists(workspace_dir):
            import shutil

            shutil.rmtree(workspace_dir)
            logger.info("Workspace cleaned up successfully")
    except Exception as e:
        logger.error(f"Failed to clean up workspace: {str(e)}")
