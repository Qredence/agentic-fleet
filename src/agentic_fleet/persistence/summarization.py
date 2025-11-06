"""Summarization policy for conversation history management."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING, Any

from openai import AsyncOpenAI

if TYPE_CHECKING:
    from .repositories import MessageRepository, ReasoningRepository


class SummarizationPolicy:
    """Manages conversation history summarization to keep contexts manageable."""

    def __init__(
        self,
        threshold: int = 20,
        keep_recent: int = 6,
        openai_client: AsyncOpenAI | None = None,
    ) -> None:
        """Initialize summarization policy.

        Args:
            threshold: Message count threshold to trigger summarization
            keep_recent: Number of recent messages to preserve
            openai_client: Optional OpenAI client for summary generation
        """
        self.threshold = threshold
        self.keep_recent = keep_recent
        self.openai_client = openai_client

    async def check_and_summarize(
        self,
        conversation_id: str,
        message_repo: MessageRepository,
        reasoning_repo: ReasoningRepository | None = None,
    ) -> dict[str, Any] | None:
        """Check if summarization is needed and execute if so.

        Args:
            conversation_id: Conversation ID
            message_repo: Message repository
            reasoning_repo: Optional reasoning repository

        Returns:
            Summary metadata if summarization was performed, None otherwise
        """
        message_count = await message_repo.count(conversation_id)

        if message_count <= self.threshold:
            return None

        # Get messages to summarize (oldest messages, excluding recent ones)
        messages = await message_repo.get_history(conversation_id)
        messages_to_summarize = messages[: -self.keep_recent]

        if not messages_to_summarize:
            return None

        # Generate summary
        summary_text = await self._generate_summary(messages_to_summarize)

        # Get sequence range
        start_sequence = messages_to_summarize[0]["sequence"]
        end_sequence = messages_to_summarize[-1]["sequence"]

        # Delete summarized messages
        await message_repo.delete_range(conversation_id, start_sequence, end_sequence)

        # Note: Reasoning traces are preserved via foreign key constraint
        # They remain in reasoning_traces table for audit

        return {
            "summary_text": summary_text,
            "original_message_count": len(messages_to_summarize),
            "original_message_ids": [m["id"] for m in messages_to_summarize],
            "sequence_range": [start_sequence, end_sequence],
        }

    async def _generate_summary(self, messages: list[dict[str, Any]]) -> str:
        """Generate summary text from messages.

        Args:
            messages: List of message dictionaries

        Returns:
            Summary text
        """
        if not self.openai_client:
            # Fallback: simple concatenation summary
            return self._create_fallback_summary(messages)

        # Build conversation context
        conversation_text = "\n\n".join(
            [f"{msg['role'].upper()}: {msg['content']}" for msg in messages if msg.get("content")]
        )

        # Generate LLM summary
        try:
            response = await self.openai_client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {
                        "role": "system",
                        "content": "You are a helpful assistant that creates concise summaries of conversations. "
                        "Preserve key facts, decisions, and action items. Be factual and objective.",
                    },
                    {
                        "role": "user",
                        "content": f"Summarize this conversation history:\n\n{conversation_text}",
                    },
                ],
                max_tokens=500,
                temperature=0.3,
            )

            return response.choices[0].message.content or self._create_fallback_summary(messages)

        except Exception as exc:
            import logging

            logging.error("Summarization failed: %s", exc, exc_info=True)
            # Fallback on any error
            return self._create_fallback_summary(messages)

    def _create_fallback_summary(self, messages: list[dict[str, Any]]) -> str:
        """Create simple fallback summary.

        Args:
            messages: List of message dictionaries

        Returns:
            Fallback summary text
        """
        user_messages = [m for m in messages if m["role"] == "user"]
        assistant_messages = [m for m in messages if m["role"] == "assistant"]

        return (
            f"[Summary of {len(messages)} messages: "
            f"{len(user_messages)} user messages, "
            f"{len(assistant_messages)} assistant responses. "
            f"Key topics discussed and actions taken have been preserved in context.]"
        )


async def create_summary_message(
    message_repo: MessageRepository,
    conversation_id: str,
    sequence: int,
    summary_metadata: dict[str, Any],
) -> None:
    """Create a system message containing conversation summary.

    Args:
        message_repo: Message repository
        conversation_id: Conversation ID
        sequence: Sequence number for summary message
        summary_metadata: Summary metadata from check_and_summarize
    """
    summary_content = (
        f"**Conversation Summary**\n\n"
        f"{summary_metadata['summary_text']}\n\n"
        f"_Summarized {summary_metadata['original_message_count']} messages._"
    )

    await message_repo.add(
        message_id=f"{conversation_id}-summary-{sequence}",
        conversation_id=conversation_id,
        sequence=sequence,
        role="system",
        content=summary_content,
        reasoning=json.dumps(
            {
                "type": "summarization",
                "original_message_ids": summary_metadata["original_message_ids"],
                "sequence_range": summary_metadata["sequence_range"],
            }
        ),
    )
