"""
Routes for task management.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Request

from agentic_fleet.api.dependencies.services import get_task_service
from agentic_fleet.schemas.task import Task, TaskCreate, TaskUpdate
from agentic_fleet.services.task_service import TaskService

# Create router
router = APIRouter()


@router.get("/", response_model=Dict[str, List[Task]])
async def list_tasks(task_service: TaskService = Depends(get_task_service)) -> Dict[str, List[Task]]:
    """
    List all tasks.
    
    Returns a list of all tasks in the system with their current status,
    assigned agents, and progress information.
    
    Returns:
        Dict containing a list of all tasks
    """
    try:
        tasks = await task_service.list_tasks()
        return {"tasks": tasks}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/", response_model=Task)
async def create_task(task: TaskCreate, task_service: TaskService = Depends(get_task_service)) -> Task:
    """
    Create a new task.
    """
    try:
        return await task_service.create_task(task)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{task_id}", response_model=Task)
async def get_task(task_id: str, task_service: TaskService = Depends(get_task_service)) -> Task:
    """
    Get details for a specific task.
    """
    try:
        task = await task_service.get_task(task_id)
        if not task:
            raise HTTPException(status_code=404, detail=f"Task {task_id} not found")
        return task
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/{task_id}", response_model=Task)
async def update_task(task_id: str, task: TaskUpdate, task_service: TaskService = Depends(get_task_service)) -> Task:
    """
    Update an existing task.
    """
    try:
        updated_task = await task_service.update_task(task_id, task)
        if not updated_task:
            raise HTTPException(status_code=404, detail=f"Task {task_id} not found")
        return updated_task
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{task_id}", response_model=Dict[str, bool])
async def delete_task(task_id: str, task_service: TaskService = Depends(get_task_service)) -> Dict[str, bool]:
    """
    Delete a task.
    """
    try:
        success = await task_service.delete_task(task_id)
        if not success:
            raise HTTPException(status_code=404, detail=f"Task {task_id} not found")
        return {"success": True}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{task_id}/assign/{agent_id}", response_model=Task)
async def assign_task(task_id: str, agent_id: str, task_service: TaskService = Depends(get_task_service)) -> Task:
    """
    Assign a task to an agent.
    
    Assigns a specific task to a specific agent. The agent will begin
    working on the task according to its capabilities and current workload.
    
    Args:
        task_id: The unique identifier of the task to assign
        agent_id: The unique identifier of the agent to assign the task to
        
    Returns:
        The updated task with assignment information
        
    Raises:
        HTTPException: 404 if task or agent not found
    """
    try:
        task = await task_service.assign_task(task_id, agent_id)
        if not task:
            raise HTTPException(status_code=404, detail=f"Task {task_id} not found")
        return task
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
