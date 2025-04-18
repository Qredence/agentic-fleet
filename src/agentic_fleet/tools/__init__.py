"""
Tools module for AgenticFleet.

This module contains tool implementations for various tasks.

DEPRECATED: This module is deprecated and will be replaced by agentic_fleet.tool_pool in a future version.
The tool_pool module provides a more modular, base-class approach to tool implementation.
"""

import warnings

# Show deprecation warning
warnings.warn(
    "The agentic_fleet.tools module is deprecated and will be replaced by agentic_fleet.tool_pool in a future version. "
    "The tool_pool module provides a more modular, base-class approach to tool implementation.",
    DeprecationWarning,
    stacklevel=2
)

from .bing_search import bing_search_tool
from .calculator import calculator_tool
from .fetch_webpage import fetch_webpage_tool
from .generate_image import generate_image_tool
from .generate_pdf import generate_pdf_tool
from .google_search import google_search_tool

__all__ = [
    "bing_search_tool",
    "calculator_tool",
    "google_search_tool",
    "generate_image_tool",
    "generate_pdf_tool",
    "fetch_webpage_tool",
]
