"""
Services module for AgenticFleet.

This module contains business logic services that are used by the application,
including client management, message processing, and other core functionality.
"""

from agentic_fleet.services.client_factory import create_client, get_cached_client
from agentic_fleet.services.message_processing import process_response, stream_text

__all__ = ["create_client", "get_cached_client", "process_response", "stream_text"]
