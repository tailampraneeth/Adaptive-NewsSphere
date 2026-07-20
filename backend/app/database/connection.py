import logging
from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from app.core.config import settings

logger = logging.getLogger("adaptive-newssphere.database")

# Initialize the async engine
DATABASE_URL = settings.get_database_url()
logger.info(f"Connecting to database via async driver: {DATABASE_URL.split('@')[-1]}")

if "sqlite" in DATABASE_URL:
    engine = create_async_engine(
        DATABASE_URL,
        echo=False,
        pool_pre_ping=True
    )
else:
    engine = create_async_engine(
        DATABASE_URL,
        echo=False,  # Set True to output generated SQL statements
        pool_size=10,
        max_overflow=20,
        pool_pre_ping=True
    )

# Async session factory
AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False
)

async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency yielding an asynchronous database session, ensuring auto-close."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
        except Exception as e:
            logger.error(f"Database session encountered error, rolling back: {e}")
            await session.rollback()
            raise
        finally:
            await session.close()
