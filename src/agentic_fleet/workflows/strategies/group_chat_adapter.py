"""DSPy-powered Group Chat Manager and Builder.

This module provides an adapter for managing group chats using DSPy for
speaker selection and termination decisions, plus a builder pattern for
easy configuration.
"""

from __future__ import annotations

from typing import Any

from agent_framework._types import ChatMessage, Role

from ...dspy_modules.reasoner import DSPyReasoner
from ...utils.logger import setup_logger

logger = setup_logger(__name__)


# =============================================================================
# GroupChatBuilder
# =============================================================================


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


# =============================================================================
# DSPyGroupChatManager
# =============================================================================


class DSPyGroupChatManager:
    """Manager for group chats using DSPy for orchestration."""

    def __init__(
        self,
        agents: list[Any],
        reasoner: DSPyReasoner,
        max_rounds: int = 10,
        admin_name: str = "Admin",
    ) -> None:
        """Initialize the group chat manager.

        Args:
            agents: List of participating agents
            reasoner: DSPy reasoner instance
            max_rounds: Maximum number of conversation rounds
            admin_name: Name of the admin agent (default: "Admin")
        """
        self.agents = {agent.name: agent for agent in agents}
        self.agent_names = list(self.agents.keys())
        self.reasoner = reasoner
        self.max_rounds = max_rounds
        self.admin_name = admin_name
        self.history: list[ChatMessage] = []

    async def run_chat(
        self,
        initial_message: str,
        sender: str = "User",
    ) -> list[ChatMessage]:
        """Run the group chat loop.

        Args:
            initial_message: The starting message
            sender: The sender of the initial message

        Returns:
            List of chat messages from the conversation
        """
        self.history = [
            ChatMessage(
                role=Role.USER, text=initial_message, additional_properties={"name": sender}
            )
        ]

        current_speaker = sender
        rounds = 0

        while rounds < self.max_rounds:
            # Select next speaker
            next_speaker_name = await self._select_next_speaker(current_speaker)

            if next_speaker_name == "TERMINATE" or next_speaker_name not in self.agents:
                logger.info(f"Group chat terminated by {next_speaker_name}")
                break

            logger.info(f"Next speaker selected: {next_speaker_name}")

            # Execute agent
            agent = self.agents[next_speaker_name]

            try:
                if hasattr(agent, "run"):
                    # Pass the full history to the agent
                    # Note: We pass the history as messages.
                    # The agent's run method should handle list[ChatMessage].
                    try:
                        response_obj = await agent.run(messages=self.history)
                    except TypeError as e:
                        logger.warning(
                            f"Agent {next_speaker_name}.run() does not accept 'messages' parameter: {e}. "
                            "Falling back to process method or mock response."
                        )
                        # Try fallback to process method
                        if hasattr(agent, "process") and self.history:
                            last_msg = self.history[-1]
                            response = await agent.process(last_msg)
                        else:
                            response = ChatMessage(
                                role=Role.ASSISTANT,
                                text=f"Mock response from {next_speaker_name} (method signature mismatch)",
                                additional_properties={"name": next_speaker_name},
                            )
                        self.history.append(response)
                        current_speaker = next_speaker_name
                        rounds += 1
                        continue

                    # Extract the last message from the response
                    if response_obj.messages:
                        response = response_obj.messages[-1]
                        # Ensure name is set by creating a new ChatMessage to avoid mutating frozen objects
                        additional_props = response.additional_properties or {}
                        if "name" not in additional_props:
                            response = ChatMessage(
                                role=response.role,
                                text=response.text,
                                additional_properties={
                                    **additional_props,
                                    "name": next_speaker_name,
                                },
                            )
                    else:
                        response = ChatMessage(
                            role=Role.ASSISTANT,
                            text=response_obj.text or "",
                            additional_properties={"name": next_speaker_name},
                        )
                elif hasattr(agent, "process"):
                    # Legacy or mock support
                    last_msg = self.history[-1]
                    response = await agent.process(last_msg)
                else:
                    # Fallback
                    response = ChatMessage(
                        role=Role.ASSISTANT,
                        text=f"Mock response from {next_speaker_name}",
                        additional_properties={"name": next_speaker_name},
                    )

                # Ensure response is ChatMessage
                if not isinstance(response, ChatMessage):
                    # If it's a WorkflowOutputEvent or similar, extract data
                    if (
                        hasattr(response, "data")
                        and isinstance(response.data, list)
                        and len(response.data) > 0
                    ):
                        response = response.data[-1]
                    else:
                        # Fallback
                        response = ChatMessage(
                            role=Role.ASSISTANT,
                            text=str(response),
                            additional_properties={"name": next_speaker_name},
                        )

                self.history.append(response)
                current_speaker = next_speaker_name
                rounds += 1

            except Exception as e:
                logger.error(f"Error executing agent {next_speaker_name}: {e}")
                break

        return self.history

    async def _select_next_speaker(self, last_speaker: str) -> str:
        """Select the next speaker using DSPy."""

        # Format history for DSPy
        history_str = "\n".join(
            [
                f"{msg.additional_properties.get('name', 'unknown')}: {msg.text}"
                for msg in self.history
            ]
        )

        # Format participants
        participants_str = "\n".join(
            [
                f"- {name}: {getattr(agent, 'description', 'No description')}"
                for name, agent in self.agents.items()
            ]
        )

        result = self.reasoner.select_next_speaker(
            history=history_str, participants=participants_str, last_speaker=last_speaker
        )

        return result["next_speaker"]
