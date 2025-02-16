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
from agentic_fleet.config import config_manager

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
STREAM_DELAY = env_config.get("stream_delay", 0.01)
PORT = int(os.getenv("PORT", "8001"))
HOST = os.getenv("HOST", "localhost")

# Get default values
defaults = config_manager.get_defaults()
DEFAULT_MAX_ROUNDS = defaults.get("max_rounds", 10)
DEFAULT_MAX_TIME = defaults.get("max_time", 300)
DEFAULT_MAX_STALLS = defaults.get("max_stalls", 3)
DEFAULT_START_PAGE = defaults.get("start_page", "/welcome")

async def stream_text(text: str) -> AsyncGenerator[str, None]:
    """Stream text content word by word."""
    words = text.split()
    for i, word in enumerate(words):
        await asyncio.sleep(STREAM_DELAY)
        yield word + (" " if i < len(words) - 1 else "")

# OAuth configuration - only define callback if OAuth is enabled
security_config = config_manager.get_security_settings()
if security_config.get("use_oauth", False):
    @oauth_callback
    async def handle_oauth_callback(
        provider_id: str,
        token: str,
        raw_user_data: Dict[str, str],
        default_user: User,
    ) -> User:
        """Handle OAuth authentication callback."""
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
                "system_prompt", defaults.get("system_prompt")
            )
        else:
            # Apply manual settings
            temperature = float(new_settings.get("temperature", 0.7))
            max_rounds = int(new_settings.get("max_rounds", 10))
            max_time = int(new_settings.get("max_time", 300))
            system_prompt = new_settings.get(
                "system_prompt", defaults.get("system_prompt")
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

@cl.set_chat_profiles
async def chat_profiles():
    """Define chat profiles with improved descriptions and settings."""
    fleet_config = config_manager.get_team_settings("magentic_fleet_one")
    profiles = []
    
    for profile_name, profile_data in fleet_config.get("chat_profiles", {}).items():
        profiles.append(
            cl.ChatProfile(
                name=profile_data["name"],
                markdown_description=profile_data["description"],
                icon=profile_data["icon"],
                default=profile_data.get("default", False),
                metadata=profile_data["settings"]
            )
        )
    
    return profiles

@cl.on_chat_start
async def start() -> None:
    """Initialize user session and set up agent team."""
    global app_manager

    try:
        logger.info("Loading application settings...")
        
        # Initialize settings with loaded configurations
        settings = Settings(
            model_configs=config_manager.get_model_settings("azure"),
            fleet_config=config_manager.get_team_settings("magentic_fleet_one")
        )

        # Store settings in session
        cl.user_session.set("settings", settings)

        # Get security configuration
        security_config = config_manager.get_security_settings()
        logger.info(
            f"OAuth enabled: {security_config.get('use_oauth')}, "
            f"Providers: {security_config.get('oauth_providers', [])}"
        )

        # Check OAuth configuration if enabled
        if security_config.get("use_oauth"):
            oauth_error = check_oauth_configuration()
            if oauth_error:
                logger.error(f"OAuth configuration error: {oauth_error}")
                await Message(
                    content=f"⚠️ OAuth Configuration Error:\n{oauth_error}"
                ).send()
                security_config["use_oauth"] = False
                logger.info("OAuth has been disabled due to configuration errors")

        # Get default model configuration
        default_model = config_manager.get_model_settings("azure", "o3-mini")

        # Initialize model client with configuration
        model_client = AzureOpenAIChatCompletionClient(
            azure_deployment=settings.AZURE_OPENAI_DEPLOYMENT,
            model=default_model["name"],
            azure_endpoint=settings.AZURE_OPENAI_ENDPOINT,
            api_key=settings.AZURE_OPENAI_API_KEY,
            api_version=settings.AZURE_OPENAI_API_VERSION,
            model_info=default_model
        )

        # Create and start application manager
        global app_manager
        app_manager = ApplicationManager(model_client)
        app_manager.settings = settings
        await app_manager.start()

        # Register cleanup handler
        app_manager.add_cleanup_handler(cleanup_workspace)

        # Initialize specialized agents
        env_config = config_manager.get_environment_settings()
        
        web_surfer_config = config_manager.get_agent_settings("web_surfer")
        surfer = MultimodalWebSurfer(
            name="WebSurfer",
            model_client=app_manager.model_client,
            description=web_surfer_config["description"],
            downloads_folder=env_config["downloads_dir"],
            debug_dir=env_config["debug_dir"],
            headless=True,
            start_page=user_session.get("start_page", DEFAULT_START_PAGE),
            animate_actions=False,
            to_save_screenshots=True,
            use_ocr=False,
            to_resize_viewport=True,
        )

        file_surfer_config = config_manager.get_agent_settings("file_surfer")
        file_surfer = FileSurfer(
            name="FileSurfer",
            model_client=app_manager.model_client,
            description=file_surfer_config["description"]
        )

        coder = MagenticOneCoderAgent(
            name="Coder",
            model_client=app_manager.model_client
        )

        # Create code executor
        workspace_dir = os.path.join(os.getcwd(), env_config["workspace_dir"])
        code_executor = LocalCommandLineCodeExecutor(
            work_dir=workspace_dir,
            timeout=config_manager.get_agent_settings("executor")["config"]["timeout"]
        )

        # Create executor agent
        executor = CodeExecutorAgent(
            name="Executor",
            code_executor=code_executor,
            description=config_manager.get_agent_settings("executor")["description"],
        )

        # Get active chat profile
        active_profile = user_session.get("active_chat_profile", "MagenticFleet One")
        
        # Initialize team based on active profile
        team_config = config_manager.get_team_settings(active_profile.lower().replace(" ", "_"))
        
        if active_profile == "MagenticFleet One":
            team = MagenticOneGroupChat(
                model_client=model_client,
                participants=[surfer, file_surfer, coder, executor],
                max_turns=user_session.get("max_rounds", DEFAULT_MAX_ROUNDS),
                max_stalls=user_session.get("max_stalls", DEFAULT_MAX_STALLS),
            )
        else:
            # Use SelectorGroupChat for other profiles
            agents = [
                locals()[agent_name.lower()]
                for agent_name in team_config["participants"]
            ]
            team = SelectorGroupChat(
                agents=agents,
                model_client=model_client,
                termination_conditions=[
                    MaxMessageTermination(max_messages=team_config["config"]["max_messages"]),
                    TextMentionTermination(text="DONE", ignore_case=True)
                ],
                selector_description=team_config["config"]["selector_description"]
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
        for directory in [env_config["workspace_dir"], env_config["debug_dir"], env_config["downloads_dir"]]:
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
    """Process a single message with proper formatting and step visualization."""
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
                    task_list.tasks.clear()
                    task_list.status = "Creating tasks..."
                    await task_list.send()

                    # Add tasks with delays for visual feedback
                    for step in steps:
                        task = cl.Task(
                            title=step["title"],
                            status=cl.TaskStatus.READY,
                            description=step["description"] if step["description"] else None
                        )
                        await task_list.add_task(task)
                        await cl.sleep(0.2)

                    task_list.status = "Ready to execute..."
                    await task_list.send()
                    plan_step.output = f"Created plan with {len(steps)} steps"

        # Format content based on message type
        if isinstance(message, TextMessage):
            step_name = f"Message from {source}"
            async with Step(name=step_name, type="message") as msg_step:
                msg_step.input = content
                msg = Message(content="", author=source)
                async for chunk in stream_text(content):
                    await msg.stream_token(chunk)
                await msg.send()
                collected_responses.append(content)
                msg_step.output = "Message processed"

        elif isinstance(message, MultiModalMessage):
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
            async with Step(name="Generic Message", type="other") as gen_step:
                gen_step.input = content
                msg = Message(content="", author="System")
                async for chunk in stream_text(content):
                    await msg.stream_token(chunk)
                await msg.send()
                collected_responses.append(content)
                gen_step.output = "Message processed"

    except Exception as e:
        logger.error(f"Error processing message: {str(e)}")
        await Message(content=f"⚠️ Error processing message: {str(e)}").send()

def extract_steps_from_content(content: str) -> List[Dict[str, str]]:
    """Extract steps from the content with their descriptions.
    
    Returns:
        List of dictionaries with 'title' and 'description' keys
    """
    steps = []
    if "Here is the plan to follow as best as possible:" in content:
        plan_section = content.split("Here is the plan to follow as best as possible:")[1].strip()
        current_step = None
        
        for line in plan_section.split("\n"):
            line = line.strip()
            if not line:
                continue
                
            if line.startswith(("• ", "- ", "* ")):
                if current_step:
                    steps.append(current_step)
                    
                step_text = line[2:].strip()
                step_text = re.sub(r"\*\*|\`\`\`|\*", "", step_text)
                step_text = re.sub(r"\s+", " ", step_text)
                
                current_step = {
                    "title": step_text,
                    "description": ""
                }
            elif current_step:
                if current_step["description"]:
                    current_step["description"] += " "
                current_step["description"] += line
                
        if current_step:
            steps.append(current_step)
            
    return steps

async def _process_multimodal_message(content: List[Any]) -> None:
    """Process a multimodal message containing text and images."""
    try:
        for item in content:
            if isinstance(item, Image):
                image_data = getattr(item, "data", None) or getattr(
                    item, "content", None
                )
                if image_data:
                    await _handle_image_data(image_data)

    except Exception as e:
        logger.error(f"Error processing multimodal message: {str(e)}")
        await Message(content=f"⚠️ Error processing multimodal message: {str(e)}").send()

async def _handle_image_data(image_data: Union[str, bytes]) -> Optional[Image]:
    """Handle image data processing and display."""
    try:
        if isinstance(image_data, str):
            if image_data.startswith(("http://", "https://")):
                image = Image(url=image_data, display="inline")
                await Message(content="📸 New screenshot:", elements=[image]).send()
                return image
            elif os.path.isfile(image_data):
                image = Image(path=image_data, display="inline")
                await Message(content="📸 New screenshot:", elements=[image]).send()
                return image
        elif isinstance(image_data, bytes):
            env_config = config_manager.get_environment_settings()
            debug_dir = os.path.join(env_config["logs_dir"], "debug")
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
    """Handle incoming user messages and coordinate agent responses."""
    try:
        async with cl.Step(name="Message Handler", type="handler", show_input=True) as current_step:
            current_step.input = message.content

            task_list = user_session.get("task_list")
            team = user_session.get("team")

            if not task_list or not team:
                current_step.is_error = True
                current_step.output = "Session not initialized"
                await Message(
                    content="⚠️ Session not initialized. Please refresh the page."
                ).send()
                return

            task_list = TaskList()
            task_list.status = "Planning..."
            await task_list.send()
            user_session.set("task_list", task_list)

            collected_responses = []
            current_task = None

            async with cl.Step(
                name="Team Processing",
                type="team",
                show_input=True
            ) as team_step:
                team_step.input = message.content
                
                async for response in team.run_stream(task=message.content):
                    await process_response(response, collected_responses)

                    if task_list.tasks:
                        for task in task_list.tasks:
                            if task.status != TaskStatus.DONE:
                                task.status = TaskStatus.RUNNING
                                current_task = task
                                break
                        await task_list.send()

                    if current_task:
                        current_task.status = TaskStatus.DONE
                        current_task = None
                        await task_list.send()

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
        team = user_session.get("team")
        if team:
            await team.cleanup()

        task_list = user_session.get("task_list")
        if task_list:
            for task in task_list.tasks:
                if task.status == cl.TaskStatus.RUNNING:
                    task.status = cl.TaskStatus.FAILED
            task_list.status = "Stopped"
            await task_list.send()

        env_config = config_manager.get_environment_settings()
        workspace_dir = os.path.join(os.getcwd(), env_config["workspace_dir"])
        if os.path.exists(workspace_dir):
            import shutil
            shutil.rmtree(workspace_dir)

    except Exception as e:
        logger.exception("Cleanup failed")
        await Message(content=f"⚠️ Cleanup error: {str(e)}").send()

def check_oauth_configuration() -> Optional[str]:
    """Check OAuth configuration and return an error message if misconfigured."""
    try:
        security_config = config_manager.get_security_settings()
        oauth_providers = security_config.get("oauth_providers", [])
        
        required_vars = {}
        for provider in oauth_providers:
            required_vars[provider["client_id_env"]] = os.getenv(provider["client_id_env"])
            required_vars[provider["client_secret_env"]] = os.getenv(provider["client_secret_env"])
        
        required_vars["OAUTH_REDIRECT_URI"] = os.getenv("OAUTH_REDIRECT_URI")

        missing_vars = [var for var, value in required_vars.items() if not value]

        if missing_vars:
            return f"Missing required OAuth environment variables: {', '.join(missing_vars)}"

        if not oauth_providers:
            return "No OAuth providers configured"

        return None

    except Exception as e:
        logger.error(f"Error checking OAuth configuration: {str(e)}")
        return f"Failed to check OAuth configuration: {str(e)}"

async def cleanup_workspace() -> None:
    """Clean up the workspace directory."""
    try:
        env_config = config_manager.get_environment_settings()
        workspace_dir = os.path.join(os.getcwd(), env_config["workspace_dir"])
        if os.path.exists(workspace_dir):
            import shutil
            shutil.rmtree(workspace_dir)
            logger.info("Workspace cleaned up successfully")
    except Exception as e:
        logger.error(f"Failed to clean up workspace: {str(e)}")
