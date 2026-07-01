import asyncio
from typing import AsyncGenerator
import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.pool import NullPool
from app.core.config import settings
from app.database.models.base import Base
from sqlalchemy import delete

# Use the configured environment database url (localhost:5433)
TEST_DATABASE_URL = settings.get_database_url()

@pytest_asyncio.fixture(scope="function")
async def test_engine():
    """
    Centralized test database engine using NullPool.
    NullPool disables connection pooling, ensuring each connection is opened/closed
    fresh. This avoids 'another operation is in progress' errors during schema drop/creation.
    """
    engine = create_async_engine(TEST_DATABASE_URL, echo=False, poolclass=NullPool)

    # Establish fresh tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)

    yield engine
    # Keep database tables intact for local development persistence
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
        # Pre-test cleanup to avoid primary key/unique collisions across files
        from app.database.models.publisher import Publisher
        from app.database.models.article import Article
        from app.database.models.story import Story
        from app.database.models.duplicate import ArticleDuplicate

        await session.execute(delete(ArticleDuplicate))
        await session.execute(delete(Article))
        await session.execute(delete(Publisher))
        await session.execute(delete(Story))
        await session.commit()

        # Pre-test Qdrant cleanup to guarantee perfect isolation
        from qdrant_client import QdrantClient
        from qdrant_client.http import models as q_models
        import time

        q_client = QdrantClient(url=settings.QDRANT_URL)
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
        time.sleep(0.2)

        yield session
        await session.rollback()
