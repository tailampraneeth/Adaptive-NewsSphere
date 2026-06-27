import asyncio
import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.pool import NullPool
from app.core.config import settings
from app.database.models.base import Base
from sqlalchemy import delete

# Use the configured environment database url (localhost:5433)
TEST_DATABASE_URL = settings.get_database_url()

@pytest.fixture(scope="session")
def event_loop():
    """
    Centralized session-scoped event loop.
    Creates a new event loop instance that persists for the entire pytest session
    and is closed only after all session-scoped fixtures teardown.
    """
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()

@pytest_asyncio.fixture(scope="session")
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
    
    # Tear down tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        
    await engine.dispose()

@pytest_asyncio.fixture(scope="function")
async def db_session(test_engine) -> AsyncSession:
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
        
        await session.execute(delete(Article))
        await session.execute(delete(Publisher))
        await session.execute(delete(Story))
        await session.commit()
        
        yield session
        await session.rollback()
