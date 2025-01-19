"""Chainlit-based web interface for AutoGen agent interactions."""

# Standard library imports
import asyncio
import json
import logging
import os
import re
import string
import time
from typing import Any, Dict, List, Optional, Union

# Third-party imports
from chainlit.input_widget import Select, Slider, TextInput
from dotenv import load_dotenv
import matplotlib.pyplot as plt
import pandas as pd
from pydantic import BaseModel, Field
import requests
import chainlit as cl

# AutoGen imports
from autogen_agentchat.agents import (
    AssistantAgent,
    CodeExecutorAgent,
    UserProxyAgent,
)
from autogen_agentchat.base import TaskResult
from autogen_agentchat.messages import (
    FunctionCall,
    Image,
    MultiModalMessage,
    TextMessage,
)
from autogen_agentchat.teams import MagenticOneGroupChat
from autogen_ext.agents.file_surfer import FileSurfer
from autogen_ext.agents.magentic_one import MagenticOneCoderAgent
from autogen_ext.agents.web_surfer import MultimodalWebSurfer
from autogen_ext.code_executors.local import LocalCommandLineCodeExecutor
from autogen_ext.models.openai import AzureOpenAIChatCompletionClient

# Initialize logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

# Constants
STREAM_DELAY = 0.01
DEFAULT_MAX_ROUNDS = 50
DEFAULT_MAX_TIME = 10
DEFAULT_MAX_STALLS = 5
DEFAULT_START_PAGE = "https://bing.com"

# Initialize Azure OpenAI client
az_model_client = AzureOpenAIChatCompletionClient(
    azure_deployment=os.getenv("AZURE_OPENAI_DEPLOYMENT", "gpt-4o-fleet"),
    model=os.getenv("AZURE_OPENAI_MODEL", "gpt-4o-2024-11-20"),
    api_version=os.getenv("AZURE_OPENAI_API_VERSION", "2024-08-01-preview"),
    azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
    api_key=os.getenv("AZURE_OPENAI_API_KEY"),
    model_info={
        "vision": True,
        "function_calling": True,
        "json_output": True,
    }
)


@cl.oauth_callback
async def oauth_callback(
    provider_id: str,
    token: str,
    raw_user_data: Dict[str, str],
    default_user: cl.User,
) -> cl.User:
    """Handle OAuth authentication callback.

    Args:
        provider_id: OAuth provider identifier
        token: Authentication token
        raw_user_data: Raw user data from provider
        default_user: Default user object

    Returns:
        Updated user object
    """
    try:
        # Check if OAuth is disabled via environment variable
        if os.getenv("DISABLE_OAUTH") == "1":
            logger.info("OAuth is disabled, using default user")
            return default_user

        # Handle GitHub OAuth
        if provider_id == "github":
            if not (os.getenv("OAUTH_GITHUB_CLIENT_ID") and os.getenv("OAUTH_GITHUB_CLIENT_SECRET")):
                logger.warning("GitHub OAuth credentials not found")
                return default_user

            # You can customize the user based on GitHub data
            username = raw_user_data.get("login", "")
            name = raw_user_data.get("name", "")
            email = raw_user_data.get("email", "")

            logger.info(f"Authenticated GitHub user: {username}")
            return cl.User(
                identifier=username,
                metadata={
                    "name": name,
                    "email": email,
                    "provider": "github"
                }
            )

        # Default fallback
        logger.warning(f"Unsupported OAuth provider: {provider_id}")
        return default_user

    except Exception as e:
        logger.error(f"OAuth callback error: {str(e)}")
        return default_user

@cl.on_settings_update
async def update_settings(settings: Dict[str, Any]) -> None:
    """Handle settings updates from the UI.

    Args:
        settings: Dictionary containing updated settings
    """
    # Update session settings
    cl.user_session.set("max_rounds", settings.get("max_rounds", DEFAULT_MAX_ROUNDS))
    cl.user_session.set("max_time", settings.get("max_time", DEFAULT_MAX_TIME))
    cl.user_session.set("max_stalls", settings.get("max_stalls", DEFAULT_MAX_STALLS))
    cl.user_session.set("start_page", settings.get("start_page", DEFAULT_START_PAGE))

@cl.on_chat_start
async def initialize_session() -> None:
    """Initialize user session and set up agent team."""
    try:
        # Handle user authentication
        app_user = cl.user_session.get("user")
        greeting = f"Hi {app_user.identifier}! 👋" if app_user else "Hi there! Welcome to AgenticFleet 👋"
        await cl.Message(f"{greeting} Feel free to adjust your experience in the settings above.").send()

        # Initialize chat settings
        settings = cl.ChatSettings(
            [
                Slider(
                    id="max_rounds",
                    label="Max Rounds",
                    initial=DEFAULT_MAX_ROUNDS,
                    min=1,
                    max=100,
                    step=1,
                    description="Maximum number of conversation rounds"
                ),
                Slider(
                    id="max_time",
                    label="Max Time (Minutes)",
                    initial=DEFAULT_MAX_TIME,
                    min=1,
                    max=60,
                    step=1,
                    description="Maximum time in minutes for task completion"
                ),
                Slider(
                    id="max_stalls",
                    label="Max Stalls Before Replan",
                    initial=DEFAULT_MAX_STALLS,
                    min=1,
                    max=10,
                    step=1,
                    description="Maximum number of stalls before replanning"
                ),
                TextInput(
                    id="start_page",
                    label="Start Page URL",
                    initial=DEFAULT_START_PAGE,
                    description="Default URL for web searches"
                ),
            ]
        )
        await settings.send()

        # Store default settings in session
        cl.user_session.set("max_rounds", DEFAULT_MAX_ROUNDS)
        cl.user_session.set("max_time", DEFAULT_MAX_TIME)
        cl.user_session.set("max_stalls", DEFAULT_MAX_STALLS)
        cl.user_session.set("start_page", DEFAULT_START_PAGE)

        # Initialize session parameters
        cl.user_session.set("max_rounds", DEFAULT_MAX_ROUNDS)
        cl.user_session.set("max_time", DEFAULT_MAX_TIME)
        cl.user_session.set("max_stalls", DEFAULT_MAX_STALLS)
        cl.user_session.set("start_page", DEFAULT_START_PAGE)

        # Display settings
        welcome_text = (
            "Here's your setup (easily adjustable in settings):\n\n"
            f"• Rounds: {DEFAULT_MAX_ROUNDS} conversations\n"
            f"• Time: {DEFAULT_MAX_TIME} min\n"
            f"• Stalls: {DEFAULT_MAX_STALLS} before replanning\n"
            f"• Start URL: {DEFAULT_START_PAGE}"
        )
        await cl.Message(content=welcome_text).send()

        # Create necessary directories
        workspace_dir = os.path.join(os.getcwd(), "workspace")
        debug_dir = os.path.join(os.getcwd(), "debug")
        files_dir = os.path.join(os.getcwd(), ".files")

        for directory in [workspace_dir, debug_dir, files_dir]:
            os.makedirs(directory, exist_ok=True)

        try:
            # Initialize specialized agents
            surfer = MultimodalWebSurfer(
                name="WebSurfer",
                model_client=az_model_client,
                description="""You are an expert web surfer agent. Your role is to:
                1. Navigate and extract information from web pages
                2. Take screenshots of relevant content
                3. Summarize findings in a clear, structured format""",
                start_page=cl.user_session.get("start_page", DEFAULT_START_PAGE),
                headless=True,
                animate_actions=False,
                to_save_screenshots=True,
                use_ocr=False,
                debug_dir="debug"
            )

            file_surfer = FileSurfer(
                name="FileSurfer",
                model_client=az_model_client,
                description="""You are an expert file system navigator. Your role is to:
                    1. Search and analyze files in the workspace
                    2. Extract relevant information from files
                    3. Organize and manage file operations efficiently"""
            )

            coder = MagenticOneCoderAgent(
                name="Coder",
                model_client=az_model_client
            )

            # Create code executor with proper workspace
            code_executor = LocalCommandLineCodeExecutor(
                work_dir=workspace_dir,
                timeout=300  # 5 minutes timeout
            )

            # Create executor agent
            executor = CodeExecutorAgent(
                name="Executor",
                code_executor=code_executor,
                description="""You are an expert code execution agent. Your role is to:
                    1. Safely execute code in the workspace
                    2. Monitor execution and handle timeouts
                    3. Provide detailed feedback on execution results
                    4. Maintain a clean and organized workspace"""
            )

            # Create team with improved configuration
            team = MagenticOneGroupChat(
                participants=[surfer, file_surfer, coder, executor],
                model_client=az_model_client,
                max_turns=cl.user_session.get("max_rounds", DEFAULT_MAX_ROUNDS),
                max_stalls=cl.user_session.get("max_stalls", DEFAULT_MAX_STALLS)
            )
            cl.user_session.set("team", team)

            # Initialize task list
            task_list = cl.TaskList()
            task_list.status = "Ready"
            cl.user_session.set("task_list", task_list)
            await task_list.send()

            await cl.Message(content="✅ Your multi-agent team is ready! Each agent has been initialized with specialized capabilities.").send()

        except Exception as agent_error:
            logger.error(f"Failed to initialize agents: {str(agent_error)}")
            await cl.Message(content=f"⚠️ Failed to initialize agents: {str(agent_error)}").send()
            raise

    except Exception as e:
        logger.exception("Failed to initialize session")
        await cl.Message(content=f"⚠️ Session initialization failed: {str(e)}").send()


async def process_response(response: Any, collected_responses: List[str]) -> None:
    """Process agent responses while preserving agent attribution and showing inner messages.

    Args:
        response: Agent response to process
        collected_responses: List to collect processed responses
    """
    try:
        # Handle TaskResult objects
        if isinstance(response, TaskResult):
            for msg in response.messages:
                await process_message(msg, collected_responses)
            if response.stop_reason:
                await cl.Message(
                    content=f"🛑 Task stopped: {response.stop_reason}",
                    author="System"
                ).send()
            return

        # Handle TextMessage objects directly
        if isinstance(response, TextMessage):
            await process_message(response, collected_responses)
            return

        # Handle chat messages
        if hasattr(response, 'chat_message'):
            await process_message(response.chat_message, collected_responses)
            return

        # Handle inner thoughts and reasoning
        if hasattr(response, 'inner_monologue'):
            await cl.Message(
                content=f"💭 Inner thought: {response.inner_monologue}",
                author="System",
                indent=1
            ).send()
            return

        # Handle function calls
        if hasattr(response, 'function_call'):
            await cl.Message(
                content=f"🛠️ Function call: {response.function_call}",
                author="System",
                indent=1
            ).send()
            return

        # Handle multimodal messages (images, etc.)
        if isinstance(response, (list, tuple)):
            await _process_multimodal_message(response)
            return

        # Handle any other type of response
        content = str(response)
        await cl.Message(content=content, author="System").send()
        collected_responses.append(content)

    except Exception as e:
        logger.error(f"Error processing response: {str(e)}")
        await cl.Message(content=f"⚠️ Error processing response: {str(e)}").send()

async def process_message(message: Union[TextMessage, Any], collected_responses: List[str]) -> None:
    """Process a single message with proper formatting."""
    try:
        # Extract content and source
        content = message.content if hasattr(message, 'content') else str(message)
        source = getattr(message, 'source', 'Unknown')

        # Check for plan and update task list
        if "Here is the plan to follow as best as possible:" in content:
            task_list = cl.user_session.get("task_list")
            if task_list:
                steps = extract_steps_from_content(content)
                task_list.tasks.clear()  # Clear existing tasks
                for step in steps:
                    task = cl.Task(title=step)
                    await task_list.add_task(task)
                task_list.status = "Executing Plan..."
                await task_list.send()

        # Format content based on message type
        if isinstance(message, TextMessage):
            # Send the message with proper attribution
            await cl.Message(content=content, author=source).send()
            collected_responses.append(content)
        elif isinstance(message, MultiModalMessage):
            # Only process the images from multimodal content
            for item in message.content:
                if isinstance(item, Image):
                    image_data = getattr(item, 'data', None) or getattr(item, 'content', None)
                    if image_data:
                        await _handle_image_data(image_data)
        elif isinstance(message, FunctionCall):
            # Handle function calls
            await cl.Message(
                content=f"🛠️ Function: {message.name}\nArgs: {json.dumps(message.args, indent=2)}",
                author=source,
                indent=1
            ).send()
        else:
            # Handle other message types
            await cl.Message(content=content, author=source).send()
            collected_responses.append(content)

    except Exception as e:
        logger.error(f"Error processing message: {str(e)}")
        await cl.Message(content=f"⚠️ Error processing message: {str(e)}").send()

def extract_steps_from_content(content: str) -> List[str]:
    """Extract steps from the content.

    Args:
        content: Content string to extract steps from

    Returns:
        List of extracted steps
    """
    steps = []
    if "Here is the plan to follow as best as possible:" in content:
        plan_section = content.split("Here is the plan to follow as best as possible:")[1].strip()
        # Split by bullet points and filter out empty lines
        for line in plan_section.split("\n"):
            line = line.strip()
            if line.startswith(("- ", "* ")):
                # Remove the bullet point and clean up
                step = line[2:].strip()
                if step:
                    # Remove markdown formatting and extra whitespace
                    step = re.sub(r'\*\*|\`\`\`|\*', '', step)
                    step = re.sub(r'\s+', ' ', step)
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
                image_data = getattr(item, 'data', None) or getattr(item, 'content', None)
                if image_data:
                    await _handle_image_data(image_data)

    except Exception as e:
        logger.error(f"Error processing multimodal message: {str(e)}")
        await cl.Message(content=f"⚠️ Error processing multimodal message: {str(e)}").send()

async def _handle_image_data(image_data: Union[str, bytes]) -> Optional[cl.Image]:
    """Handle image data processing and display.

    Args:
        image_data: Image data as string or bytes
    """
    try:
        if isinstance(image_data, str):
            if image_data.startswith(('http://', 'https://')):
                # Display remote images directly
                image = cl.Image(url=image_data, display="inline")
                await cl.Message(content="📸 New screenshot:", elements=[image]).send()
                return image
            elif os.path.isfile(image_data):
                # Display local images
                image = cl.Image(path=image_data, display="inline")
                await cl.Message(content="📸 New screenshot:", elements=[image]).send()
                return image
        elif isinstance(image_data, bytes):
            # Save and display bytes data
            logs_dir = os.path.join(os.getcwd(), "logs")
            debug_dir = os.path.join(logs_dir, "debug")
            os.makedirs(debug_dir, exist_ok=True)
            temp_path = os.path.join(debug_dir, f"screenshot_{int(time.time())}.png")
            with open(temp_path, "wb") as f:
                f.write(image_data)
            image = cl.Image(path=temp_path, display="inline")
            await cl.Message(content="📸 New screenshot:", elements=[image]).send()
            return image

    except Exception as e:
        logger.error(f"Error handling image data: {str(e)}")
        await cl.Message(content=f"⚠️ Error handling image: {str(e)}").send()

    return None


@cl.on_message
async def handle_message(message: cl.Message):
    """Handle incoming user messages and coordinate agent responses."""
    try:
        # Get task list and team from session
        task_list = cl.user_session.get("task_list")
        team = cl.user_session.get("team")

        if not task_list or not team:
            await cl.Message(content="⚠️ Session not initialized. Please refresh the page.").send()
            return

        # Reset task list for new message
        task_list = cl.TaskList()
        task_list.status = "Planning..."
        await task_list.send()
        cl.user_session.set("task_list", task_list)

        # Process message with team
        collected_responses = []
        current_task = None

        async for response in team.run_stream(task=message.content):
            # Process the response
            await process_response(response, collected_responses)

            # Update task status if we have tasks
            if task_list.tasks:
                # Find first non-completed task
                for task in task_list.tasks:
                    if task.status != cl.TaskStatus.DONE:
                        task.status = cl.TaskStatus.RUNNING
                        current_task = task
                        break
                await task_list.send()

            # Mark current task as done if we have one
            if current_task:
                current_task.status = cl.TaskStatus.DONE
                current_task = None
                await task_list.send()

        # Mark all remaining tasks as done
        for task in task_list.tasks:
            if task.status != cl.TaskStatus.DONE:
                task.status = cl.TaskStatus.DONE
        task_list.status = "Done"
        await task_list.send()

    except Exception as e:
        logger.error(f"Error processing message: {str(e)}")
        if task_list:
            task_list.status = "Failed"
            await task_list.send()
        await cl.Message(content=f"⚠️ Error processing message: {str(e)}").send()


@cl.on_stop
async def cleanup() -> None:
    """Clean up resources when the application stops."""
    try:
        # Get the team from session
        team = cl.user_session.get("team")
        if team:
            # Clean up team resources
            await team.cleanup()

        # Clean up workspace
        workspace_dir = os.path.join(os.getcwd(), "workspace")
        if os.path.exists(workspace_dir):
            import shutil
            shutil.rmtree(workspace_dir)

    except Exception as e:
        logger.exception("Cleanup failed")
        await cl.Message(content=f"⚠️ Cleanup error: {str(e)}").send()
