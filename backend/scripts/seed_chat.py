import asyncio
import os
import sys
import uuid
from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from sqlalchemy import text, select, func

# Add backend to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from app.core.config import settings
from app.database.models.user import User
from app.database.models.story import Story
from app.database.models.conversation import ChatSession, ChatMessage


async def seed_chat_session():
    db_url = settings.get_database_url()
    print("[*] Connecting to database to seed chat conversation logs...")

    # Try connecting to PostgreSQL first, fall back to SQLite test.db if unreachable
    use_sqlite = False
    try:
        engine = create_async_engine(db_url, echo=False)
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1;"))
        print("[OK] Successfully connected to PostgreSQL for chat seeding.")
    except Exception as e:
        print(
            f"[WARN] Failed to connect to PostgreSQL at {db_url}: {e}. "
            "Falling back to local SQLite test.db for chat seeding."
        )
        db_url = "sqlite+aiosqlite:///test.db"
        use_sqlite = True
        engine = create_async_engine(db_url, echo=False)

    # Ensure tables exist if SQLite is used
    if use_sqlite:
        from app.database.models.base import Base
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

    async_session = async_sessionmaker(bind=engine, expire_on_commit=False)

    async with async_session() as session:
        # Check if user already exists
        user_stmt = select(User).limit(1)
        user_res = await session.execute(user_stmt)
        user = user_res.scalar_one_or_none()

        if not user:
            user = User(id=uuid.uuid4(), email="chat_user@test.com")
            session.add(user)
            await session.commit()
            print(f"[+] Created test user: {user.email} (ID: {user.id})")

        # Check if story exists
        story_stmt = select(Story).limit(1)
        story_res = await session.execute(story_stmt)
        story = story_res.scalar_one_or_none()

        if not story:
            story = Story(
                id=uuid.uuid4(),
                title="Generative AI Progress on Mobile Hardware",
                summary="Researchers demonstrate local text generation models running on small CPU footprints.",
                importance_score=0.95,
                trending_score=0.85,
                credibility_score=0.90,
                verification_score=0.92,
                publisher_diversity=3,
                article_count=5
            )
            story.category = "Technology"
            session.add(story)
            await session.commit()
            print(f"[+] Created test story: {story.title} (ID: {story.id})")

        # Create Chat Session
        session_id = uuid.uuid4()
        chat_session = ChatSession(
            id=session_id,
            user_id=user.id,
            story_id=story.id,
            title="Generative AI Progress on Mobile Hardware",
            message_count=2
        )
        session.add(chat_session)
        await session.commit()
        print(f"[+] Created ChatSession (ID: {session_id})")

        # Add messages
        user_message = ChatMessage(
            session_id=session_id,
            sender="user",
            message="Can we run 3B parameter models locally on typical client CPUs?",
            citations=[]
        )
        
        meta = {
            "retrieval_latency_ms": 14.8,
            "llm_latency_ms": 1100.0,
            "total_latency_ms": 1114.8,
            "retrieved_article_count": 2,
            "average_similarity": 0.79,
            "highest_similarity": 0.85,
            "citations_count": 1,
            "context_size_chars": 3500,
            "token_estimate": 875,
            "history_messages_used": 0,
            "history_truncated": False,
            "retrieval_count": 1,
            "confidence": 0.82,
            "unanswered": False
        }

        assistant_message = ChatMessage(
            session_id=session_id,
            sender="assistant",
            message=(
                "Yes, according to [Source: TechDaily], optimizations in 4-bit quantization "
                "allow 3B models to run at ~15 tokens per second on mid-range x86 CPUs."
            ),
            citations=[{
                "article_id": str(uuid.uuid4()),
                "publisher_name": "TechDaily",
                "published_at": datetime.now(timezone.utc).isoformat(),
                "title": "Local LLM Benchmarks"
            }],
            prompt_version="v1",
            chat_metadata=meta
        )

        session.add_all([user_message, assistant_message])
        await session.commit()
        print("[+] Seeded conversation messages.")
        print(f"[OK] Chat session seeding completed successfully. Session ID: {session_id}")

    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(seed_chat_session())
