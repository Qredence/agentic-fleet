"""Main entry point for AgenticFleet.

This module provides the main entry point for the AgenticFleet application.
It can start either the Chainlit app directly, the FastAPI app with the Chainlit app mounted,
or the original API app.
"""

import logging
import os
import sys

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


def main():
    """Main entry point for the AgenticFleet application."""
    logger.info("Starting Agentic Fleet API server with OpenAPI documentation")

    # Import necessary modules
    # It's good practice to keep imports at the top, but for app and create_tables,
    # they are specific to this function's logic of starting the server.
    # If 'app' was used elsewhere, it would be at the top.
    from agentic_fleet.api.main import app  # FastAPI app instance
    from agentic_fleet.database.session import create_tables

    # Initialize database
    try:
        create_tables()
        logger.info("Database tables created successfully.")
    except Exception as e:
        logger.error(f"Database initialization failed: {e}", exc_info=True)
        logger.info(
            "Continuing without database initialization. Some features may not work as expected."
        )

    # Get configuration from environment variables
    host = os.environ.get("HOST", "0.0.0.0")
    port = int(os.environ.get("PORT", "8000")) # Default to 8000 if not set
    reload = os.environ.get("RELOAD", "False").lower() == "true"

    if reload:
        logger.info("Auto-reload is enabled. Server will restart on code changes.")

    logger.info(f"Agentic Fleet API will be available at http://{host}:{port}")
    logger.info(f"OpenAPI documentation: http://{host}:{port}/docs")
    logger.info(f"ReDoc documentation: http://{host}:{port}/redoc")

    try:
        uvicorn.run(
            "agentic_fleet.api.main:app",  # Path to the FastAPI app instance
            host=host,
            port=port,
            reload=reload,
            log_level="info", # Uvicorn's own logging level
        )
    except Exception as e:
        logger.critical(f"Failed to start Agentic Fleet API server: {e}", exc_info=True)
        sys.exit(1)
    finally:
        logger.info("Agentic Fleet API server has shut down.")


if __name__ == "__main__":
    main()
