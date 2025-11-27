"""Builder for DSPy-powered Group Chats.

This module provides a builder pattern for creating and configuring
DSPyGroupChatManager instances.
"""

from __future__ import annotations

from typing import Any

from ..dspy_modules.reasoner import DSPyReasoner
from .group_chat_adapter import DSPyGroupChatManager


class GroupChatBuilder:
    """Builder for DSPyGroupChatManager."""

    def __init__(self) -> None:
        """Initialize the builder."""
        self.agents: list[Any] = []
        self.reasoner: DSPyReasoner | None = None
        self.max_rounds: int = 10
        self.admin_name: str = "Admin"

    def add_agent(self, agent: Any) -> GroupChatBuilder:
        """Add an agent to the group chat."""
        self.agents.append(agent)
        return self

    def set_reasoner(self, reasoner: DSPyReasoner) -> GroupChatBuilder:
        """Set the DSPy reasoner."""
        self.reasoner = reasoner
        return self

    def set_max_rounds(self, max_rounds: int) -> GroupChatBuilder:
        """Set the maximum number of rounds."""
        self.max_rounds = max_rounds
        return self

    def set_admin_name(self, admin_name: str) -> GroupChatBuilder:
        """Set the admin name."""
        self.admin_name = admin_name
        return self

    def build(self) -> DSPyGroupChatManager:
        """Build the DSPyGroupChatManager instance."""
        if not self.agents:
            raise ValueError("At least one agent must be added to the group chat.")
        if not self.reasoner:
            # Create a default reasoner if none provided
            self.reasoner = DSPyReasoner()

        return DSPyGroupChatManager(
            agents=self.agents,
            reasoner=self.reasoner,
            max_rounds=self.max_rounds,
            admin_name=self.admin_name,
        )
