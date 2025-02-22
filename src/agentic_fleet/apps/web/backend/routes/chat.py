"""
Chat routing module for AgenticFleet.

This module handles HTTP endpoints related to chat functionality,
including message history and agent configuration.
"""

from typing import List, Dict, Any, Optional
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field
from datetime import datetime

from ..services.agent_service import AgentService

router = APIRouter(prefix="/api/chat", tags=["chat"])

class Message(BaseModel):
    """Message model for chat interactions."""
    content: str
    sender: str
    timestamp: float = Field(default_factory=lambda: datetime.now().timestamp())
    metadata: Dict[str, Any] = {}

class ChatHistory(BaseModel):
    """Chat history model containing a list of messages."""
    messages: List[Message]
    session_id: str
    agent_name: str
    created_at: float = Field(default_factory=lambda: datetime.now().timestamp())

class AgentUpdate(BaseModel):
    """Model for agent configuration updates."""
    parameters: Dict[str, Any]

# In-memory storage for chat histories
chat_histories: Dict[str, ChatHistory] = {}

async def get_agent_service() -> AgentService:
    """Dependency injection for AgentService."""
    service = AgentService()
    await service.initialize_agents()
    return service

@router.get("/agents")
async def list_agents(
    service: AgentService = Depends(get_agent_service)
) -> Dict[str, List[Dict[str, Any]]]:
    """
    List available agents and their capabilities.
    
    Returns:
        Dict containing agent information
    """
    return {
        "agents": service.get_available_agents()
    }

@router.get("/agents/{agent_name}")
async def get_agent_details(
    agent_name: str,
    service: AgentService = Depends(get_agent_service)
) -> Dict[str, Any]:
    """
    Get detailed information about a specific agent.
    
    Args:
        agent_name: Name of the agent
        
    Returns:
        Dict containing agent details
        
    Raises:
        HTTPException: If agent not found
    """
    try:
        return service.get_agent_info(agent_name)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

@router.patch("/agents/{agent_name}/config")
async def update_agent_configuration(
    agent_name: str,
    update: AgentUpdate,
    service: AgentService = Depends(get_agent_service)
) -> Dict[str, str]:
    """
    Update an agent's configuration parameters.
    
    Args:
        agent_name: Name of the agent to update
        update: New configuration parameters
        
    Returns:
        Dict containing status message
        
    Raises:
        HTTPException: If agent not found or invalid parameters
    """
    try:
        await service.update_agent_config(agent_name, update.parameters)
        return {"status": "Configuration updated successfully"}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/history/{session_id}")
async def get_chat_history(session_id: str) -> ChatHistory:
    """
    Retrieve chat history for a specific session.
    
    Args:
        session_id: Unique identifier for the chat session
        
    Returns:
        ChatHistory object containing messages
        
    Raises:
        HTTPException: If session not found
    """
    if session_id not in chat_histories:
        raise HTTPException(status_code=404, detail="Chat session not found")
    return chat_histories[session_id]

@router.post("/history/{session_id}")
async def add_to_chat_history(
    session_id: str,
    message: Message
) -> Dict[str, str]:
    """
    Add a message to the chat history.
    
    Args:
        session_id: Unique identifier for the chat session
        message: Message to add to history
        
    Returns:
        Dict containing status message
    """
    if session_id not in chat_histories:
        chat_histories[session_id] = ChatHistory(
            messages=[],
            session_id=session_id,
            agent_name=message.metadata.get("agent_name", "unknown")
        )
    
    chat_histories[session_id].messages.append(message)
    return {"status": "Message added to history"}

@router.delete("/history/{session_id}")
async def clear_chat_history(session_id: str) -> Dict[str, str]:
    """
    Clear chat history for a specific session.
    
    Args:
        session_id: Unique identifier for the chat session
        
    Returns:
        Dict containing status message
        
    Raises:
        HTTPException: If session not found
    """
    if session_id not in chat_histories:
        raise HTTPException(status_code=404, detail="Chat session not found")
    
    del chat_histories[session_id]
    return {"status": "Chat history cleared"}
