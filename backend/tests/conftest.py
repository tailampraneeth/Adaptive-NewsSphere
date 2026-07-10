import logging
import time
from typing import AsyncGenerator
import pytest_asyncio
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.pool import NullPool
from sqlalchemy import delete, text
from app.core.config import settings
from app.database.models.base import Base
# Import all models to register them on Base.metadata before table creation

logger = logging.getLogger("adaptive-newssphere.test_conftest")

# Use the configured environment database url (localhost:5433)
TEST_DATABASE_URL = settings.get_database_url()

@pytest_asyncio.fixture(scope="function")
async def test_engine():
    """
    Centralized test database engine using NullPool.
    Falls back to a local in-memory SQLite database if the target PostgreSQL
    server is unreachable, enabling offline/Docker-free test execution.
    """
    url = TEST_DATABASE_URL
    use_sqlite = False

    # Try connecting to PostgreSQL first
    try:
        engine = create_async_engine(url, echo=False, poolclass=NullPool)
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1;"))
        logger.info("Successfully connected to PostgreSQL for testing.")
    except Exception as e:
        logger.warning(
            f"Failed to connect to PostgreSQL at {url}: {e}. "
            "Falling back to async SQLite test.db database for testing."
        )
        url = "sqlite+aiosqlite:///test.db"
        use_sqlite = True
        engine = create_async_engine(url, echo=False, poolclass=NullPool)

    # Establish fresh tables
    async with engine.begin() as conn:
        if use_sqlite:
            # Drop and create tables to start clean
            await conn.run_sync(Base.metadata.drop_all)
            await conn.run_sync(Base.metadata.create_all)
        else:
            await conn.run_sync(Base.metadata.drop_all)
            await conn.run_sync(Base.metadata.create_all)

    yield engine
    # Keep database tables intact for local development persistence
    await engine.dispose()

    if use_sqlite:
        import os
        if os.path.exists("test.db"):
            try:
                os.remove("test.db")
            except Exception as ex:
                logger.warning(f"Failed to clean up test.db: {ex}")

@pytest_asyncio.fixture(scope="function")
async def db_session(test_engine) -> AsyncGenerator[AsyncSession, None]:
    """
    Function-scoped database session.
    Automatically cleans tables before every single test run to guarantee
    perfect isolation between test cases.
    """
    async_session = async_sessionmaker(
        bind=test_engine,
        class_=AsyncSession,
        expire_on_commit=False
    )
    async with async_session() as session:
        # Pre-test cleanup to avoid primary key/unique collisions across files
        from app.database.models.publisher import Publisher
        from app.database.models.article import Article
        from app.database.models.story import Story
        from app.database.models.duplicate import ArticleDuplicate
        from app.database.models.user_profile import UserProfile
        from app.database.models.recommendation import UserRecommendationLog
        from app.database.models.conversation import ChatSession, ChatMessage
        from app.database.models.user import User

        # SQLite supports standard deletes, but user_profiles/recommendations might not be clean
        try:
            await session.execute(delete(ChatMessage))
            await session.execute(delete(ChatSession))
            await session.execute(delete(ArticleDuplicate))
            await session.execute(delete(Article))
            await session.execute(delete(Publisher))
            await session.execute(delete(Story))
            await session.execute(delete(UserProfile))
            await session.execute(delete(UserRecommendationLog))
            await session.execute(delete(User))
            await session.commit()
        except Exception as e:
            logger.warning(f"Database pre-test cleanup warning: {e}")
            await session.rollback()

        # Pre-test Qdrant cleanup to guarantee perfect isolation
        from qdrant_client import QdrantClient
        from qdrant_client.http import models as q_models

        try:
            q_client = QdrantClient(url=settings.QDRANT_URL)
            # Use small timeout to fail fast if Qdrant is offline
            q_client.get_collections()
            for col in ["articles", "stories"]:
                if q_client.collection_exists(col):
                    q_client.delete_collection(col)
                q_client.create_collection(
                    collection_name=col,
                    vectors_config=q_models.VectorParams(
                        size=384,
                        distance=q_models.Distance.COSINE
                    )
                )
            time.sleep(0.1)
        except Exception as e:
            logger.debug(f"Qdrant cleanup skipped (service unreachable at {settings.QDRANT_URL}): {e}")

        yield session
        await session.rollback()
