"""FastAPI application for AgenticFleet.

This module provides a FastAPI application that mounts the Chainlit app.
"""

import logging
import os
import subprocess
import sys
from pathlib import Path
from typing import Dict, List, Optional

import uvicorn
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

# Initialize logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI(
    title="AgenticFleet API",
    description="API for AgenticFleet",
    version="0.1.0",
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/", response_class=HTMLResponse)
async def root():
    """Root endpoint that redirects to the Chainlit UI."""
    return """
    <html>
        <head>
            <title>AgenticFleet API</title>
            <meta http-equiv="refresh" content="0;url=/ui" />
        </head>
        <body>
            <p>Redirecting to <a href="/ui">Chainlit UI</a>...</p>
        </body>
    </html>
    """


@app.get("/api/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "ok"}


@app.get("/api/models")
async def get_models():
    """Get available models."""
    try:
        from agentic_fleet.config.llm_config_manager import llm_config_manager
        models = llm_config_manager.get_all_models()
        return {"models": models}
    except Exception as e:
        logger.error(f"Error getting models: {e}")
        return JSONResponse(
            status_code=500,
            content={"error": f"Error getting models: {str(e)}"},
        )


@app.get("/api/profiles")
async def get_profiles():
    """Get available profiles."""
    try:
        from agentic_fleet.config.llm_config_manager import llm_config_manager
        profiles = llm_config_manager.get_all_profiles()
        return {"profiles": profiles}
    except Exception as e:
        logger.error(f"Error getting profiles: {e}")
        return JSONResponse(
            status_code=500,
            content={"error": f"Error getting profiles: {str(e)}"},
        )


def start_chainlit_server():
    """Start the Chainlit server as a subprocess."""
    # Get the path to the chainlit_app.py file
    chainlit_app_path = os.path.join(
        Path(__file__).parent.parent, "chainlit_app.py"
    )
    
    # Get configuration from environment variables
    host = os.environ.get("CHAINLIT_HOST", "127.0.0.1")
    port = int(os.environ.get("CHAINLIT_PORT", "8000"))
    
    # Build the command to start the Chainlit server
    cmd = [
        "chainlit", "run",
        chainlit_app_path,
        "--host", host,
        "--port", str(port),
        "--headless",  # Run in headless mode
    ]
    
    logger.info(f"Starting Chainlit server: {' '.join(cmd)}")
    
    # Start the Chainlit server as a subprocess
    process = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    
    # Log the process ID
    logger.info(f"Chainlit server started with PID {process.pid}")
    
    return process


def mount_chainlit_app():
    """Mount the Chainlit app to the FastAPI app."""
    # Get the path to the Chainlit static files
    chainlit_static_dir = os.path.join(
        Path.home(), ".chainlit", "frontend"
    )
    
    # Check if the directory exists
    if not os.path.exists(chainlit_static_dir):
        logger.warning(f"Chainlit static directory not found: {chainlit_static_dir}")
        logger.warning("Chainlit UI will not be available")
        return
    
    # Mount the Chainlit static files
    app.mount(
        "/ui",
        StaticFiles(directory=chainlit_static_dir, html=True),
        name="chainlit",
    )
    
    logger.info(f"Mounted Chainlit UI at /ui from {chainlit_static_dir}")


def run_server():
    """Run the FastAPI server."""
    # Start the Chainlit server
    chainlit_process = start_chainlit_server()
    
    # Mount the Chainlit app
    mount_chainlit_app()
    
    # Get configuration from environment variables
    host = os.environ.get("API_HOST", "0.0.0.0")
    port = int(os.environ.get("API_PORT", "8080"))
    
    # Run the FastAPI server
    uvicorn.run(
        "agentic_fleet.api.fastapi_app:app",
        host=host,
        port=port,
        reload=True,
    )
    
    # Terminate the Chainlit server when the FastAPI server stops
    chainlit_process.terminate()


if __name__ == "__main__":
    run_server()
