"""Conversation service."""

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload

from agentic_fleet.api.db import models
from agentic_fleet.api.schemas import chat as chat_schema


async def create_conversation(db: AsyncSession, title: str | None = None) -> models.Conversation:
    """Create a new conversation."""
    new_conversation = models.Conversation(title=title or "New Conversation")
    db.add(new_conversation)
    try:
        await db.commit()
        await db.refresh(new_conversation)

        # Re-fetch with eager loading to ensure messages are loaded for Pydantic
        stmt = (
            select(models.Conversation)
            .options(selectinload(models.Conversation.messages))
            .filter(models.Conversation.id == new_conversation.id)
        )
        result = await db.execute(stmt)
        conversation = result.scalars().first()
        if not conversation:
            raise ValueError("Failed to retrieve created conversation")
        return conversation
    except Exception:
        await db.rollback()
        raise


async def get_conversation(db: AsyncSession, conversation_id: int) -> models.Conversation | None:
    """Get a conversation by ID."""
    stmt = (
        select(models.Conversation)
        .options(selectinload(models.Conversation.messages))
        .filter(models.Conversation.id == conversation_id)
        .execution_options(populate_existing=True)
    )

    result = await db.execute(stmt)
    return result.scalars().first()


async def list_conversations(db: AsyncSession) -> list[models.Conversation]:
    """List all conversations."""
    result = await db.execute(
        select(models.Conversation)
        .options(selectinload(models.Conversation.messages))
        .order_by(models.Conversation.created_at.desc())
    )
    conversations = result.scalars().all()
    return list(conversations)


async def add_message_to_conversation(
    db: AsyncSession, conversation_id: int, message: chat_schema.Message
) -> models.Message:
    """Add a message to a conversation."""
    new_message = models.Message(
        conversation_id=conversation_id,
        content=message.content,
        role=message.role,
        reasoning=message.reasoning,
    )
    db.add(new_message)
    await db.commit()
    await db.refresh(new_message)
    return new_message


async def get_messages_for_conversation(
    db: AsyncSession, conversation_id: int
) -> list[models.Message]:
    """Get messages for a conversation."""
    result = await db.execute(
        select(models.Message)
        .filter(models.Message.conversation_id == conversation_id)
        .order_by(models.Message.created_at.asc())
    )
    messages = result.scalars().all()
    return list(messages)
