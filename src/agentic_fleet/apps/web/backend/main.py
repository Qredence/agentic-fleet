"""
FastAPI main application module for AgenticFleet.

This module initializes the FastAPI application and sets up core middleware,
WebSocket handlers, and agent management for the chat interface.
"""

from pathlib import Path
from typing import Any, Dict

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from agentic_fleet.core.application import create_application

from .routes import chat
from .services.agent_service import AgentService

# Initialize FastAPI app
app = FastAPI(title="AgenticFleet API")

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, replace with specific origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Get the current file's directory
current_dir = Path(__file__).parent
static_dir = current_dir.parent / "frontend" / "static"

# Mount static files
app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

# Include chat routes
app.include_router(chat.router)

# Application state
class AppState:
    """Application state container."""
    agent_service: AgentService = None
    app_manager = None

app_state = AppState()

@app.on_event("startup")
async def startup_event():
    """Initialize application state on startup."""
    # Create and initialize application manager
    app_state.app_manager = create_application()
    await app_state.app_manager.initialize()
    
    # Initialize agent service
    app_state.agent_service = AgentService()
    await app_state.agent_service.initialize_agents()

@app.on_event("shutdown")
async def shutdown_event():
    """Clean up resources on shutdown."""
    if app_state.app_manager:
        await app_state.app_manager.shutdown()

@app.websocket("/api/chat")
async def websocket_endpoint(websocket: WebSocket):
    """
    WebSocket endpoint for real-time chat with agents.
    
    Args:
        websocket: WebSocket connection instance
    """
    await websocket.accept()
    
    try:
        while True:
            # Receive message from client
            data = await websocket.receive_json()
            
            # Process message through agent service
            response = await app_state.agent_service.process_message(
                message=data["content"],
                agent_name=data.get("agent"),
                metadata=data.get("metadata", {})
            )
            
            # Send response back to client
            await websocket.send_json(response)
            
    except WebSocketDisconnect:
        print("Client disconnected")
    except Exception as e:
        print(f"Error in WebSocket handler: {str(e)}")
        await websocket.send_json({
            "sender": "system",
            "content": f"Error processing message: {str(e)}",
            "error": True
        })
    finally:
        await websocket.close()

@app.get("/")
async def root():
    """Serve the main HTML page."""
    return FileResponse(str(static_dir / "index.html"))
