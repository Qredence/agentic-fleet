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
    
    Note: Future versions may support query parameters for filtering by status,
    assigned agent, priority, or pagination (limit, offset).
    
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
    
    Creates a new task that can be assigned to agents for execution.
    The task will be created with a pending status and can be assigned later.
    
    Args:
        task: Task creation data including title, description, and requirements
        
    Returns:
        The created task with assigned ID and initial status
        
    Raises:
        HTTPException: 500 if creation fails
    """
    try:
        return await task_service.create_task(task)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{task_id}", response_model=Task)
async def get_task(task_id: str, task_service: TaskService = Depends(get_task_service)) -> Task:
    """
    Get details for a specific task.
    
    Retrieves detailed information about a specific task including its
    status, assigned agent, progress, and execution history.
    
    Args:
        task_id: The unique identifier of the task
        
    Returns:
        Task object with detailed information
        
    Raises:
        HTTPException: 404 if task not found
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
    
    Updates the details, status, or configuration of an existing task.
    Only provided fields will be updated; others remain unchanged.
    
    Args:
        task_id: The unique identifier of the task to update
        task: Task update data with fields to modify
        
    Returns:
        The updated task with new configuration
        
    Raises:
        HTTPException: 404 if task not found, 500 if update fails
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
    
    Permanently removes a task from the system. This action cannot be undone.
    If the task is currently assigned to an agent, it will be unassigned first.
    
    Args:
        task_id: The unique identifier of the task to delete
        
    Returns:
        Dict with success status
        
    Raises:
        HTTPException: 404 if task not found, 500 if deletion fails
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
