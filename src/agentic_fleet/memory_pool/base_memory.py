"""Base memory implementation.

This module provides a base memory implementation that can be extended by other memory types.
"""

from typing import Any, Dict, List, Optional


class BaseMemory:
    """Base memory implementation."""

    def __init__(self, name: str, description: str = "", **kwargs: Any):
        """Initialize the base memory.

        Args:
            name: The name of the memory
            description: A description of the memory
            **kwargs: Additional parameters for the memory
        """
        self.name = name
        self.description = description
        self.kwargs = kwargs
        self.data: Dict[str, Any] = {}

    async def add(self, key: str, value: Any) -> None:
        """Add a value to the memory.

        Args:
            key: The key to store the value under
            value: The value to store
        """
        self.data[key] = value

    async def get(self, key: str) -> Optional[Any]:
        """Get a value from the memory.

        Args:
            key: The key to retrieve the value for

        Returns:
            The value if found, None otherwise
        """
        return self.data.get(key)

    async def delete(self, key: str) -> None:
        """Delete a value from the memory.

        Args:
            key: The key to delete
        """
        if key in self.data:
            del self.data[key]

    async def clear(self) -> None:
        """Clear all values from the memory."""
        self.data.clear()
