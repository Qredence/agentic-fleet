import json
import logging
import traceback
import time
from typing import Dict, List, Optional, Any, Tuple, Union

import chainlit as cl
from autogen_agentchat.messages import ChatMessage, MultiModalMessage, TextMessage
from chainlit import Message, Step, Task, TaskList, TaskStatus, Text, user_session, Action

from agentic_fleet.message_processing import process_response
from agentic_fleet.ui.task_manager import extract_and_add_plan_tasks

logger = logging.getLogger(__name__)


async def handle_chat_message(message: cl.Message) -> None:
    """Process an incoming chat message and generate a response.
    
    Args:
        message: The incoming chat message
    """
    # Create an enhanced TaskList with icons
    task_list = cl.TaskList(
        title="🔄 Processing Request",
        status="Analyzing your query...",
    )
    await task_list.send()

    # Store the task list in user session for later updates
    cl.user_session.set("current_task_list", task_list)

    # Initialize plan steps tracking
    cl.user_session.set("plan_steps", {})
    cl.user_session.set("plan_tasks", {})

    try:
        # Check for reset command without showing a message
        # Handle both string and list content types
        if (
            isinstance(message.content, str)
            and message.content.strip().lower() == "/reset"
        ):
            await on_reset(
                cl.Action(name="reset_agents", payload={"action": "reset"})
            )
            task_list.status = "✅ Agents reset successfully"
            await task_list.send()
            return

        # Get agent team from user session
        team = cl.user_session.get("agent_team")
        if not team:
            # Raise error if team is missing
            raise ValueError("Agent team not initialized")

        # Update task list with processing task
        process_task = cl.Task(
            title="🧠 Processing with Agent Team",
            status=cl.TaskStatus.RUNNING,
            icon="🔄",
        )
        await task_list.add_task(process_task)

        # Create a list to collect responses
        collected_responses = []
        
        # Create status elements for tracking
        task_status = {
            "overview": cl.Text(
                name="task_overview", content="📊 **Task Overview:**\n", display="side"
            ),
            "planning": cl.Text(
                name="planning", content="🧩 **Planning:**\n", display="side"
            ),
            "execution": cl.Text(
                name="execution", content="⚙️ **Execution:**\n", display="side"
            ),
            "results": cl.Text(
                name="results", content="🎯 **Results:**\n", display="side"
            ),
        }

        # Send a dummy message first to get a message_id
        dummy_message = await cl.Message(content="").send()
        message_id = dummy_message.id
        
        # Send each status element with the message_id
        for element in task_status.values():
            await element.send(for_id=message_id)

        # Process input with agent team
        with cl.Step("System", "Processing your request") as step:
            async for chunk in team.run_stream(
                task=message.content
            ):
                # Process the response
                response_text, plan_update = await process_response(chunk)

                if response_text:
                    collected_responses.append(response_text)
                    step.output = "".join(collected_responses)
                    await step.update()
                
                # If a plan was detected, extract tasks
                if plan_update:
                    await extract_and_add_plan_tasks(
                        plan_update, 
                        task_list, 
                        task_status, 
                        message_id, 
                        is_update=len(cl.user_session.get("plan_steps", {})) > 0
                    )

        # Mark process task as complete
        process_task.status = cl.TaskStatus.DONE
        process_task.title = "✅ Processing complete"
        await task_list.update_task(process_task)
        
        # Set final output
        final_response = "".join(collected_responses)
        task_list.status = "✅ Response complete"
        await task_list.send()
        
        # Send final message with actions
        await cl.Message(
            content=final_response,
            actions=[
                cl.Action(
                    name="refine_response", 
                    label="🔄 Refine Response", 
                    description="Ask the agent to refine this response"
                ),
                cl.Action(
                    name="save_response", 
                    label="💾 Save Response", 
                    description="Save this response for later"
                )
            ]
        ).send()
    
    except Exception as e:
        # Log the error
        logger.error(f"Error processing message: {str(e)}")
        logger.error(traceback.format_exc())
        
        # Update task_list to show failure
        task_list.status = f"⚠️ Error: {str(e)}"
        await task_list.send()
        
        # Send error message to user
        await cl.Message(
            content=f"An error occurred while processing your request: {str(e)}",
        ).send()


async def on_reset(action: cl.Action) -> None:
    """Reset the agent team.
    
    Args:
        action: The action triggering the reset
    """
    # Clear the session
    cl.user_session.clear()
    
    # Reinitialize the application
    await cl.Message(content="🔄 Resetting agent team...").send()
    
    # Trigger chat restart
    await cl.ChatRestartEvent().send()


async def _handle_plan_creation(content: str, task_list: TaskList, message_id: str):
    """Handle the creation of a new plan.
    
    Args:
        content: The content containing the plan
        task_list: The task list to update
        message_id: The ID of the message
    """
    # Update the task list
    plan_task = cl.Task(
        title="📋 Plan Created",
        status=cl.TaskStatus.RUNNING,
        icon="📝",
    )
    await task_list.add_task(plan_task)
    task_list.status = "🔄 Executing plan..."
    await task_list.send()

    # Extract the plan from the content
    plan_text = content.split(
        "Here is the plan to follow as best as possible:"
    )[1].strip()

    # Create task status tracking
    task_status = {
        "planning": cl.Text(
            name="planned_tasks", content="", display="side"
        ),
        "overview": cl.Text(
            name="task_overview", content="", display="side"
        ),
        "completion": cl.Text(
            name="completed_tasks", content="", display="side"
        ),
        "execution": cl.Text(
            name="execution_progress",
            content="",
            display="side",
        ),
    }

    # Extract and add individual plan steps as tasks
    await extract_and_add_plan_tasks(
        plan_text, task_list, task_status, message_id
    )


async def _handle_plan_update(content: str, task_list: TaskList, message_id: str):
    """Handle updates to an existing plan.
    
    Args:
        content: The content containing the plan update
        task_list: The task list to update
        message_id: The ID of the message
    """
    # Extract the updated plan
    for marker in [
        "Updated plan:",
        "Next steps:",
        "Additional steps:",
        "Revised plan:",
    ]:
        if marker in content:
            plan_update = content.split(marker)[1].strip()
            task_status = {
                "planning": cl.Text(
                    name="planned_tasks",
                    content="",
                    display="side",
                ),
                "overview": cl.Text(
                    name="task_overview",
                    content="",
                    display="side",
                ),
                "completion": cl.Text(
                    name="completed_tasks",
                    content="",
                    display="side",
                ),
                "execution": cl.Text(
                    name="execution_progress",
                    content="",
                    display="side",
                ),
            }
            await extract_and_add_plan_tasks(
                plan_update,
                task_list,
                task_status,
                message_id,
                is_update=True,
            )
            break


def _rename_author(orig_author: str) -> str:
    """Friendly agent names with emoji indicators.
    
    Args:
        orig_author: The original author name
        
    Returns:
        A formatted author name with emoji
    """
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
