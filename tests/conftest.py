"""
Pytest configuration and fixtures for AgenticFleet tests.

This module provides common fixtures and configuration for all tests,
including setting up required environment variables.
"""

import os

# Set environment variables before any imports happen
# This ensures Settings can be initialized during module imports
os.environ.setdefault("OPENAI_API_KEY", "test-openai-key")
os.environ.setdefault("AZURE_AI_PROJECT_ENDPOINT", "https://test-project.openai.azure.com")
os.environ.setdefault("AZURE_AI_SEARCH_ENDPOINT", "https://test-service.search.windows.net")
os.environ.setdefault("AZURE_AI_SEARCH_KEY", "test-search-key")
os.environ.setdefault("AZURE_OPENAI_CHAT_COMPLETION_DEPLOYED_MODEL_NAME", "gpt-4o")
os.environ.setdefault("AZURE_OPENAI_EMBEDDING_DEPLOYED_MODEL_NAME", "text-embedding-ada-002")
