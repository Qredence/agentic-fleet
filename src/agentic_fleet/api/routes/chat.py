"""
Routes for chat functionality.
"""

import json
from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, Request, WebSocket, WebSocketDisconnect

from agentic_fleet.api.dependencies.services import get_chat_service
from agentic_fleet.schemas.message import Message as ChatMessage
from agentic_fleet.schemas.message import MessageCreate as ChatMessageCreate
from agentic_fleet.schemas.message import MessageUpdate as ChatMessageUpdate
from agentic_fleet.services.chat_service import ChatService

# Create router
router = APIRouter()


@router.get("/messages", response_model=Dict[str, List[ChatMessage]])
async def list_messages(
    session_id: str, chat_service: ChatService = Depends(get_chat_service)
) -> Dict[str, List[ChatMessage]]:
    """
    List all chat messages for a session.
    
    Retrieves the complete chat history for a specific session, including
    messages from both users and AI agents.

    Args:
        session_id: The ID of the session to get messages for
        
    Returns:
        Dict containing a list of chat messages for the session
        
    Raises:
        HTTPException: 500 if retrieval fails
    """
    try:
        messages = await chat_service.get_chat_history(session_id)
        return {"messages": messages}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/messages", response_model=ChatMessage)
async def create_message(
    message: ChatMessageCreate, chat_service: ChatService = Depends(get_chat_service)
) -> ChatMessage:
    """
    Create a new chat message.
    
    Sends a message to the chat system and processes it through the AI agents.
    The message will be stored and may trigger responses from assigned agents.
    
    Args:
        message: Chat message data including content, sender, and session info
        
    Returns:
        The created message with assigned ID and timestamp
        
    Raises:
        HTTPException: 500 if message processing fails
    """
    try:
        return await chat_service.process_message(message)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/messages/{message_id}", response_model=ChatMessage)
async def get_message(message_id: str, chat_service: ChatService = Depends(get_chat_service)) -> ChatMessage:
    """
    Get a specific chat message.
    
    Retrieves detailed information about a specific chat message including
    its content, metadata, and processing status.
    
    Args:
        message_id: The unique identifier of the message
        
    Returns:
        Chat message object with detailed information
        
    Raises:
        HTTPException: 404 if message not found
    """
    try:
        message = await chat_service.get_message(message_id)
        if not message:
            raise HTTPException(status_code=404, detail=f"Message {message_id} not found")
        return message
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/messages/{message_id}", response_model=ChatMessage)
async def update_message(
    message_id: str, message: ChatMessageUpdate, chat_service: ChatService = Depends(get_chat_service)
) -> ChatMessage:
    """
    Update a chat message.
    
    Updates the content or metadata of an existing chat message.
    Only provided fields will be updated; others remain unchanged.
    
    Args:
        message_id: The unique identifier of the message to update
        message: Message update data with fields to modify
        
    Returns:
        The updated message with new content
        
    Raises:
        HTTPException: 404 if message not found, 500 if update fails
    """
    try:
        updated_message = await chat_service.update_message(message_id, message)
        if not updated_message:
            raise HTTPException(status_code=404, detail=f"Message {message_id} not found")
        return updated_message
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/messages/{message_id}", response_model=Dict[str, bool])
async def delete_message(message_id: str, chat_service: ChatService = Depends(get_chat_service)) -> Dict[str, bool]:
    """
    Delete a chat message.
    
    Permanently removes a chat message from the system. This action cannot be undone.
    The message will be removed from the chat history.
    
    Args:
        message_id: The unique identifier of the message to delete
        
    Returns:
        Dict with success status
        
    Raises:
        HTTPException: 404 if message not found, 500 if deletion fails
    """
    try:
        success = await chat_service.delete_message(message_id)
        if not success:
            raise HTTPException(status_code=404, detail=f"Message {message_id} not found")
        return {"success": True}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket, chat_service: ChatService = Depends(get_chat_service)):
    """
    WebSocket endpoint for real-time chat.
    
    Establishes a WebSocket connection for real-time bidirectional communication
    with the AI agents. Messages can be sent and received in real-time.
    
    The WebSocket accepts JSON messages with the following format:
    ```json
    {
        "content": "Your message here",
        "session_id": "optional_session_id",
        "agent_id": "optional_specific_agent"
    }
    ```
    
    Or plain text messages which will be treated as content.
    """
    await websocket.accept()

    # Generate a session ID for this connection
    session_id = f"session_{uuid4().hex}"

    await chat_service.register_websocket(session_id, websocket)
    try:
        while True:
            data_text = await websocket.receive_text()
            # Parse the JSON data
            data = {}
            try:
                data = json.loads(data_text)
            except json.JSONDecodeError:
                # If not valid JSON, treat as plain text message
                data = {"content": data_text}

            await chat_service.process_websocket_message(session_id, data)
    except WebSocketDisconnect:
        await chat_service.unregister_websocket(session_id)
