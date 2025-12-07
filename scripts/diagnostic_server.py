import logging
import os
import sys
import traceback

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.FileHandler("backend_diagnostic.log"), logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger(__name__)

try:
    logger.info("Starting diagnostic script")
    logger.info(f"CWD: {os.getcwd()}")

    # Add src to path
    src_path = os.path.join(os.getcwd(), "src")
    logger.info(f"Adding {src_path} to sys.path")
    sys.path.insert(0, src_path)

    logger.info("Attempting to import app...")
    try:
        from agentic_fleet.app.main import app

        logger.info(f"SUCCESS: App imported - {type(app)}")
    except ImportError as ie:
        logger.error(f"ImportError during app import: {ie}")
        logger.error(traceback.format_exc())
        sys.exit(1)
    except Exception as e:
        logger.error(f"Unexpected error during app import: {e}")
        logger.error(traceback.format_exc())
        sys.exit(1)

    logger.info("Importing uvicorn...")
    import uvicorn

    logger.info("Starting uvicorn run on port 8000...")
    # Use 127.0.0.1 explicitly
    uvicorn.run(app, host="127.0.0.1", port=8000, log_level="debug")

except Exception as e:
    logger.error(f"FATAL ERROR: {e}")
    logger.error(traceback.format_exc())
    sys.exit(1)
