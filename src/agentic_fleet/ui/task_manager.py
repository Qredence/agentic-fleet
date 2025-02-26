"""Module for task management functions."""

# Standard library imports
import re
import time
import logging
from typing import Dict, List, Any, Optional

# Third-party imports
import chainlit as cl
from chainlit import TaskList, TaskStatus, Text, user_session

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
from autogen_agentchat.teams import MagenticOneGroupChat
from autogen_agentchat.ui import Console
from autogen_ext.agents.file_surfer import FileSurfer
from autogen_ext.agents.magentic_one import MagenticOneCoderAgent
from autogen_ext.agents.web_surfer import MultimodalWebSurfer
from autogen_ext.code_executors.local import LocalCommandLineCodeExecutor
from autogen_ext.models.openai import AzureOpenAIChatCompletionClient

# Initialize logging
logger = logging.getLogger(__name__)

async def initialize_task_list():
    """Initialize and send the task list."""
    task_list = TaskList()
    task_list.status = "Ready"
    user_session.set("task_list", task_list)
    await task_list.send()
    return task_list

async def extract_and_add_plan_tasks(
    plan_text: str,
    task_list: Optional[cl.TaskList] = None,
    task_status: Dict[str, cl.Text] = None,
    message_id: str = None,
    is_update: bool = False,
):
    """Extract plan steps and add them as individual tasks to the TaskList.

    Args:
        plan_text: The plan text to extract steps from
        task_list: Optional TaskList instance. If not provided, will be fetched from user session
        task_status: Dictionary of Text elements for status updates
        message_id: ID of the message to associate status updates with
        is_update: Whether this is an update to an existing plan
    """
    # Added input validation
    if not isinstance(plan_text, str) or len(plan_text.strip()) == 0:
        logger.error("Invalid plan text provided")
        return

    # Get task list from session if not provided
    if task_list is None:
        task_list = cl.user_session.get("task_list")
        if task_list is None:
            logger.error("No task list found in session")
            return

    # Initialize task_status if not provided
    if task_status is None:
        task_status = {
            "planning": cl.Text(name="planned_tasks", content="", display="side"),
            "overview": cl.Text(name="task_overview", content="", display="side")
        }

    # Extract tasks using regex patterns
    tasks = []

    # Look for numbered steps (e.g., "1. Do something")
    for task in re.finditer(r"\d+\.\s+(.+?)(?=\n\d+\.|\n\n|$)", plan_text):
        tasks.append(task.group(1).strip())

    # If no numbered steps found, try looking for bullet points
    if not tasks:
        for task in re.finditer(r"[-*•]\s+(.+?)(?=\n[-*•]|\n\n|$)", plan_text):
            tasks.append(task.group(1).strip())

    # If still no tasks found, split by newlines and filter out empty lines
    if not tasks:
        tasks = [line.strip() for line in plan_text.split("\n") if line.strip()]

    if tasks:
        timestamp = time.strftime("%H:%M:%S")

        # Get existing plan steps or initialize empty dict
        plan_steps = cl.user_session.get("plan_steps", {})
        plan_tasks = cl.user_session.get("plan_tasks", {})

        # Update planning section
        planning_element = cl.Text(
            name="planned_tasks",
            content=task_status["planning"].content
            + f"\n[{timestamp}] 📋 {'Updated' if is_update else 'Initial'} Task Breakdown:\n"
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
            + f"\n[{timestamp}] 📝 {'Updated plan with' if is_update else 'Identified'} {len(tasks)} tasks to execute\n",
            display="side",
        )
        await overview_element.send(for_id=message_id)
        task_status["overview"] = overview_element

        # Add each task to the TaskList
        for i, task_text in enumerate(tasks):
            task_id = f"plan_task_{len(plan_steps) + i + 1}"

            # Create a new task in the TaskList
            plan_task_item = cl.Task(
                title=f"Step {len(plan_steps) + i + 1}: {task_text[:50]}{'...' if len(task_text) > 50 else ''}",
                status=cl.TaskStatus.READY,
                icon="📌",
            )
            await task_list.add_task(plan_task_item)

            # Store the task in the session for later reference
            plan_tasks[task_id] = plan_task_item
            plan_steps[task_id] = task_text

        # Update the session with the new tasks
        cl.user_session.set("plan_steps", plan_steps)
        cl.user_session.set("plan_tasks", plan_tasks)
        
        logger.info(f"Added {len(tasks)} tasks to the task list")


async def update_task_status(task_id: str, status: TaskStatus, message: Optional[str] = None):
    """Update the status of a task in the task list.
    
    Args:
        task_id: The ID of the task to update
        status: The new status for the task
        message: Optional message to display with the status update
    """
    plan_tasks = cl.user_session.get("plan_tasks", {})
    
    if task_id in plan_tasks:
        task = plan_tasks[task_id]
        task.status = status
        
        # Update task title with message if provided
        if message and status == TaskStatus.DONE:
            task.title = f"{task.title} ✓ {message}"
        elif message and status == TaskStatus.FAILED:
            task.title = f"{task.title} ❌ {message}"
            
        # Update the task in the session
        plan_tasks[task_id] = task
        cl.user_session.set("plan_tasks", plan_tasks)
        
        # Get the task list from the session
        task_list = cl.user_session.get("task_list")
        if task_list:
            await task_list.update_task(task)
            
        logger.info(f"Updated task {task_id} status to {status}")
    else:
        logger.warning(f"Task ID {task_id} not found in plan_tasks") 