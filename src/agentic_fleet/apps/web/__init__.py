"""
Web application package for AgenticFleet.

This package contains the FastAPI-based web interface for AgenticFleet,
including both backend API and frontend components.
"""

from .backend.main import app

__all__ = ['app']
