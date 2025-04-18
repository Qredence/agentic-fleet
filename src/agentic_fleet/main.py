"""Main entry point for AgenticFleet.

This module provides the main entry point for the AgenticFleet application.
It can start either the Chainlit app directly, the FastAPI app with the Chainlit app mounted,
or the original API app.
"""

import argparse
import logging
import os
import sys
from pathlib import Path

import uvicorn
from dotenv import load_dotenv

# Load environment variables from .env file if it exists
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger("agentic_fleet")


def run_chainlit():
    """Run the Chainlit app directly."""
    logger.info("Starting Chainlit app directly")

    # Import the chainlit_app module
    from agentic_fleet.chainlit_app import main as chainlit_main

    # Run the Chainlit app
    chainlit_main()


def run_fastapi():
    """Run the FastAPI app with the Chainlit app mounted."""
    logger.info("Starting FastAPI app with Chainlit app mounted")

    # Import the fastapi_app module
    from agentic_fleet.api.fastapi_app import run_server as fastapi_run_server

    # Run the FastAPI server
    fastapi_run_server()


def run_api():
    """Run the original API app."""
    logger.info("Starting original API app")

    # Import necessary modules
    from agentic_fleet.api.app import app
    from agentic_fleet.database.session import create_tables

    # Initialize database
    create_tables()
    logger.info("Database tables created")

    # Get configuration from environment variables
    host = os.environ.get("HOST", "0.0.0.0")
    port = int(os.environ.get("PORT", "8000"))
    reload = os.environ.get("RELOAD", "False").lower() == "true"

    logger.info(f"Starting Agentic Fleet API on {host}:{port}")

    # Run the application
    uvicorn.run(
        "agentic_fleet.api.app:app",
        host=host,
        port=port,
        reload=reload,
        log_level="info",
    )


def main():
    """Main entry point for the application."""
    # Parse command line arguments
    parser = argparse.ArgumentParser(description="AgenticFleet")
    parser.add_argument(
        "--mode",
        choices=["chainlit", "fastapi", "api"],
        default="chainlit",
        help="Mode to run the application in (default: chainlit)",
    )
    args = parser.parse_args()

    # Run the application in the specified mode
    if args.mode == "chainlit":
        run_chainlit()
    elif args.mode == "fastapi":
        run_fastapi()
    elif args.mode == "api":
        run_api()
    else:
        logger.error(f"Unknown mode: {args.mode}")
        sys.exit(1)


if __name__ == "__main__":
    main()
