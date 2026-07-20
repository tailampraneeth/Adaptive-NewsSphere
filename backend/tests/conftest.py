import logging
from typing import AsyncGenerator
import pytest_asyncio
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.pool import NullPool
from sqlalchemy import delete, text
from app.core.config import settings
from app.database.models.base import Base

logger = logging.getLogger("heimdall.test_conftest")

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

    try:
        if "sqlite" in url:
            raise ValueError("SQLite cannot be used as target PostgreSQL DB")
        engine = create_async_engine(url, echo=False, poolclass=NullPool)
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1;"))
        logger.info("Successfully connected to PostgreSQL for testing.")
    except Exception as e:
        logger.warning(
            f"Failed to connect to PostgreSQL at {url}: {e}. "
            "Falling back to async SQLite :memory: database for testing."
        )
        url = "sqlite+aiosqlite:///:memory:"
        use_sqlite = True
        from sqlalchemy.pool import StaticPool
        engine = create_async_engine(
            url,
            echo=False,
            poolclass=StaticPool,
            connect_args={"check_same_thread": False}
        )

    # Establish fresh tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)

    yield engine
    await engine.dispose()


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
        # Pre-test cleanup to avoid collisions
        from app.database.models.publisher import Publisher
        from app.database.models.article import Article
        from app.database.models.story import Story, StoryRelation
        from app.database.models.user import User
        from app.database.models.bookmark import Bookmark
        from app.database.models.reading_history import ReadingHistory

        try:
            await session.execute(delete(Bookmark))
            await session.execute(delete(ReadingHistory))
            await session.execute(delete(Article))
            await session.execute(delete(Publisher))
            await session.execute(delete(StoryRelation))
            await session.execute(delete(Story))
            await session.execute(delete(User))
            await session.commit()
        except Exception as e:
            logger.warning(f"Database pre-test cleanup warning: {e}")
            await session.rollback()

        yield session
        await session.rollback()
