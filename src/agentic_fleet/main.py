"""
Chainlit-based web interface for AutoGen agent interactions.
"""

import logging
from typing import Any, Dict, Optional

import chainlit as cl
from autogen_agentchat.messages import TextMessage
from autogen_core import CancellationToken
from autogen_ext.models.openai import AzureOpenAIChatCompletionClient

# Logging configuration
logger = logging.getLogger(__name__)

# Placeholder configuration and agent functions
def load_config() -> Dict[str, Any]:
    """Load default configuration."""
    return {
        "default_model": "o3-mini",
        "max_tokens": 4096,
    }

def validate_config(config: Dict[str, Any]) -> bool:
    """Validate configuration."""
    return bool(config.get("default_model"))

def get_registry(config: Dict[str, Any]) -> Dict[str, Any]:
    """Get agent registry."""
    return {}

def get_interaction_settings(config: Dict[str, Any]) -> Dict[str, Any]:
    """Get interaction settings."""
    return {}

def get_agent_config(agent_type: str, config: Dict[str, Any]) -> Dict[str, Any]:
    """Get agent-specific configuration."""
    return {}

# Placeholder agent classes
class PlannerAgent:
    """Placeholder for PlannerAgent."""
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}

class OrchestratorAgent:
    """Placeholder for OrchestratorAgent."""
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}

class CapabilityAssessorAgent:
    """Placeholder for CapabilityAssessorAgent."""
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}

def initialize_config() -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    """Initialize and validate configuration."""
    try:
        config = load_config()
        if not validate_config(config):
            raise RuntimeError("Invalid configuration")

        agent_registry = get_registry(config)
        interaction_settings = get_interaction_settings(config)

        return config, agent_registry, interaction_settings
    except Exception as e:
        logger.error(f"Configuration error: {str(e)}")
        raise

# Load configuration at startup
config, agent_registry, interaction_settings = initialize_config()


@cl.on_chat_start
async def start() -> None:
    """Initialize the Chainlit session."""
    try:
        # Initialize the OpenAI client
        client = AzureOpenAIChatCompletionClient(model="o3-mini")

        # Initialize agents with configuration
        planner_config = get_agent_config("planner", config)
        planner = PlannerAgent(planner_config)

        orchestrator_config = get_agent_config("orchestrator", config)
        orchestrator = OrchestratorAgent(orchestrator_config)

        assessor_config = get_agent_config("capability_assessor", config)
        capability_assessor = CapabilityAssessorAgent(assessor_config)

        # Initialize agents with proper parameters
        planner_prompt = (
            "You are a planning specialist responsible for breaking down tasks "
            "into clear, actionable steps and coordinating their execution. "
            "Your goal is to create comprehensive, strategic plans that "
            "maximize efficiency and effectiveness."
        )

        orchestrator_prompt = (
            "You are an orchestration specialist responsible for coordinating "
            "agent interactions and ensuring tasks are completed effectively."
        )

        assessor_prompt = (
            "You are a capability assessment specialist responsible for analyzing "
            "tasks and determining if the agent fleet can handle them."
        )

        # Initialize agents with proper parameters
        planner = PlannerAgent(
            name=planner_config["name"],
            description=planner_config["description"],
            prompt_template=planner_prompt,
            model_client=client,
        )

        orchestrator = OrchestratorAgent(
            name=orchestrator_config["name"],
            description=orchestrator_config["description"],
            prompt_template=orchestrator_prompt,
            model_client=client,
        )

        capability_assessor = CapabilityAssessorAgent(
            name=assessor_config["name"],
            description=assessor_config["description"],
            prompt_template=assessor_prompt,
            model_client=client,
            agent_registry=agent_registry,
        )

        # Store agents and settings in the session
        cl.user_session.set("orchestrator", orchestrator)
        cl.user_session.set("planner", planner)
        cl.user_session.set("capability_assessor", capability_assessor)
        cl.user_session.set("client", client)
        cl.user_session.set("interaction_settings", interaction_settings)

        # Create and send welcome message with markdown formatting
        agent_configs = [planner_config, orchestrator_config, assessor_config]
        capabilities_list = "\n".join(
            [
                f"* {config['name']}: **{config['description']}**\n  "
                f"_{', '.join(config.get('capabilities', []))}_"
                for config in agent_configs
            ]
        )

        welcome_msg = (
            "# 🚀 AgenticFleet System Initialized!\n\n"
            "## Available Agents and Capabilities:\n"
            f"{capabilities_list}\n\n"
            "Ready to process your requests!"
        )
        await cl.Message(content=welcome_msg).send()
        logger.info("AgenticFleet system initialized successfully")
        await cl.Message(content="Session initialized successfully!").send()

    except Exception as e:
        logger.error(f"Session initialization error: {str(e)}")
        await cl.Message(content=f"Error initializing session: {str(e)}").send()


@cl.on_message
async def main(message: cl.Message) -> None:
    """Handle incoming messages and orchestrate agent interactions."""
    try:
        # Get the orchestrator and settings from session
        orchestrator = cl.user_session.get("orchestrator")
        settings = cl.user_session.get("interaction_settings")

        if not orchestrator or not settings:
            await cl.Message(content="Session not initialized, please reload.").send()
            return

        # Set up the orchestrator with its required agents
        orchestrator.planner = cl.user_session.get("planner")
        orchestrator.capability_assessor = cl.user_session.get("capability_assessor")

        # Create a TextMessage from the user's input
        user_message = TextMessage(content=message.content, source="User")
        logger.info(f"Processing user message: {message.content}")

        # Create a task step to show progress
        async with cl.Step(name="Task Processing", type="run") as step:
            step.input = message.content

            # First, get a plan from the planner
            async with cl.Step(name="Planning", type="plan") as plan_step:
                plan_response = await orchestrator.planner.on_messages(
                    [user_message],
                    CancellationToken(),
                )
                if plan_response and plan_response.chat_message:
                    plan_msg = (
                        "## 📋 Execution Plan\n\n"
                        f"{plan_response.chat_message.content}"
                    )
                    await cl.Message(content=plan_msg, author="Planner").send()
                    logger.info("Plan generated successfully")
                    plan_step.output = "Plan created successfully"

                    # Then, assess capabilities for the plan
                    async with cl.Step(
                        name="Capability Assessment", type="assess"
                    ) as assess_step:
                        capability_response = (
                            await orchestrator.capability_assessor.on_messages(
                                [plan_response.chat_message],
                                CancellationToken(),
                            )
                        )
                        if capability_response and capability_response.chat_message:
                            assess_msg = (
                                "## 🔍 Capability Analysis\n\n"
                                f"{capability_response.chat_message.content}"
                            )
                            await cl.Message(
                                content=assess_msg, author="CapabilityAssessor"
                            ).send()
                            logger.info("Capability assessment completed")
                            assess_step.output = "Assessment completed"

                            # Finally, let the orchestrator process everything
                            async with cl.Step(
                                name="Orchestration", type="execute"
                            ) as exec_step:
                                result = await orchestrator.run(task=message.content)
                                result_msg = f"## 🎯 Task Execution\n\n{result}"
                                await cl.Message(
                                    content=result_msg, author="Orchestrator"
                                ).send()
                                logger.info("Orchestrator completed task processing")
                                exec_step.output = "Task executed successfully"
                else:
                    error_msg = "⚠️ Failed to generate a plan."
                    await cl.Message(content=error_msg).send()
                    logger.warning("Plan generation failed")
                    plan_step.output = "Plan generation failed"

            step.output = "Task processing completed"

    except Exception as e:
        error_msg = f"⚠️ Error processing message: {str(e)}"
        logger.error(error_msg)
        await cl.Message(content=error_msg).send()
