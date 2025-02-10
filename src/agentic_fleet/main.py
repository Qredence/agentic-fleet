"""
Chainlit-based web interface for AutoGen agent interactions.
"""

import logging
import os
from typing import Any, Dict, List, Optional, Sequence, Tuple

import chainlit as cl
from autogen_agentchat.messages import TextMessage
from autogen_core import CancellationToken
from autogen_ext.models.openai import OpenAIChatCompletionClient
from dotenv import load_dotenv

# Import agents and configuration
from agentic_fleet.agents import (
    BaseModelAgent,
    CapabilityAssessorAgent,
    OrchestratorAgent,
    PlannerAgent,
)
from agentic_fleet.config import (
    get_agent_config,
    get_interaction_settings,
    get_registry,
    load_config,
    validate_config,
)

# Load environment variables and configure logging
load_dotenv()
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def initialize_config() -> Tuple[Dict[str, Any], Dict[str, Any], Dict[str, Any]]:
    """Initialize and validate configuration.

    Returns:
        Tuple containing:
        - Main configuration
        - Agent registry
        - Interaction settings

    Raises:
        RuntimeError: If configuration is invalid
    """
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
        client = OpenAIChatCompletionClient(model="gpt-4")

        # Initialize agents with configuration
        planner_config = get_agent_config("planner", config)
        orchestrator_config = get_agent_config("orchestrator", config)
        assessor_config = get_agent_config("capability_assessor", config)

        # Create base prompts
        planner_prompt = (
            "You are a planning specialist responsible for breaking down tasks "
            "into clear, actionable steps and coordinating their execution."
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

    except Exception as e:
        error_msg = f"Error initializing AgenticFleet: {str(e)}"
        logger.error(error_msg)
        await cl.Message(content=f"⚠️ {error_msg}").send()


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
