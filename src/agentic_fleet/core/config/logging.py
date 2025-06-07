import logging
from agentic_fleet.config import config_manager


def setup_global_logging():
    """Configure global logging based on app_settings.yaml."""
    logging_config = config_manager.get_logging_settings()
    if logging_config and logging_config.level and logging_config.format:
        try:
            level_upper = logging_config.level.upper()
            logging.basicConfig(force=True, level=getattr(logging, level_upper, logging.INFO), format=logging_config.format)
            logging.info("Global logging configured successfully via setup_global_logging.")
        except Exception as e:
            # Fallback to basic config if error occurs, e.g., invalid log level string
            logging.basicConfig(force=True, level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
            logging.error(f"Error configuring logging from LoggingConfig: {e}. Fell back to default.")

    else:
        # Fallback to basic config if settings are incomplete
        logging.basicConfig(force=True, level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
        logging.warning("LoggingConfig not fully available or properties missing. Fell back to default logging.")

# Remove old configure_logging if it's no longer needed or alias it if it serves a different purpose.
# For now, let's assume setup_global_logging replaces its old role for basicConfig.
# def configure_logging():
#     """Configure logging for AgenticFleet."""
#     logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")

logger = logging.getLogger(__name__)
