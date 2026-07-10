import uuid
from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload

from app.database.models.conversation import ChatSession, ChatMessage
from app.database.models.story import Story

class ConversationService:
    """Manages database storage, session states, titles, and message logs for Conversational AI."""

    @staticmethod
    async def create_session(
        db: AsyncSession,
        user_id: uuid.UUID,
        story_id: uuid.UUID
    ) -> ChatSession:
        """
        Creates a new ChatSession for the story.

        Raises ValueError if story does not exist.
        """
        # Validate story exists
        story_stmt = select(Story).where(Story.id == story_id)
        res = await db.execute(story_stmt)
        story = res.scalar_one_or_none()
        if not story:
            raise ValueError(f"Story {story_id} does not exist.")

        session = ChatSession(
            user_id=user_id,
            story_id=story_id,
            title="New Conversation",
            message_count=0
        )
        db.add(session)
        await db.commit()
        await db.refresh(session)
        return session

    @staticmethod
    async def get_session(
        db: AsyncSession,
        session_id: uuid.UUID
    ) -> Optional[ChatSession]:
        """Loads a session with messages eager loaded."""
        stmt = (
            select(ChatSession)
            .where(ChatSession.id == session_id)
            .options(selectinload(ChatSession.messages))
        )
        res = await db.execute(stmt)
        return res.scalar_one_or_none()

    @staticmethod
    async def get_user_sessions(
        db: AsyncSession,
        user_id: uuid.UUID
    ) -> List[ChatSession]:
        """Loads all sessions created by the user, sorted by updated_at descending."""
        stmt = (
            select(ChatSession)
            .where(ChatSession.user_id == user_id)
            .order_by(ChatSession.updated_at.desc())
        )
        res = await db.execute(stmt)
        return list(res.scalars().all())

    @staticmethod
    async def save_message(
        db: AsyncSession,
        session_id: uuid.UUID,
        sender: str,
        message: str,
        citations: List[dict],
        prompt_version: str = "v1",
        chat_metadata: Optional[dict] = None
    ) -> ChatMessage:
        """
        Saves a message to the database.
        Increments the session's message_count and updates the title if it is the first user message.
        """
        # Load session to update count/title
        stmt = select(ChatSession).where(ChatSession.id == session_id)
        res = await db.execute(stmt)
        session = res.scalar_one_or_none()
        if not session:
            raise ValueError(f"ChatSession {session_id} does not exist.")

        # Create message
        chat_msg = ChatMessage(
            session_id=session_id,
            sender=sender,
            message=message,
            citations=citations,
            prompt_version=prompt_version,
            chat_metadata=chat_metadata
        )
        db.add(chat_msg)

        # Update session stats
        session.message_count += 1
        
        # Set title from first user message
        if sender == "user" and (session.title == "New Conversation" or not session.title):
            cleaned_msg = message.strip()
            # Truncate to first 45 chars
            session.title = cleaned_msg[:45] + ("..." if len(cleaned_msg) > 45 else "")

        await db.commit()
        await db.refresh(chat_msg)
        return chat_msg

    @staticmethod
    async def get_history(
        db: AsyncSession,
        session_id: uuid.UUID,
        max_messages: int = 10
    ) -> List[ChatMessage]:
        """Returns the last N messages of a session ordered chronologically."""
        stmt = (
            select(ChatMessage)
            .where(ChatMessage.session_id == session_id)
            .order_by(ChatMessage.created_at.desc(), ChatMessage.id.desc())
            .limit(max_messages)
        )
        res = await db.execute(stmt)
        # Reverse to get chronological order (oldest first)
        return list(reversed(res.scalars().all()))

    @staticmethod
    async def delete_session(
        db: AsyncSession,
        session_id: uuid.UUID
    ) -> bool:
        """Deletes session and all its messages (Cascade handles cleanup)."""
        stmt = select(ChatSession).where(ChatSession.id == session_id)
        res = await db.execute(stmt)
        session = res.scalar_one_or_none()
        if not session:
            return False

        await db.delete(session)
        await db.commit()
        return True
