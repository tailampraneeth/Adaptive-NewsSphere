import asyncio
import os
import sys
from sqlalchemy.ext.asyncio import create_async_engine

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.config import settings
from app.database.models.base import Base
# Import all models to ensure they are registered with Base
from app.database.models.user import User
from app.database.models.publisher import Publisher
from app.database.models.article import Article
from app.database.models.story import Story, StoryRelation
from app.database.models.timeline import StoryTimeline
from app.database.models.bookmark import Bookmark
from app.database.models.reading_history import ReadingHistory

async def init_db():
    db_url = settings.get_database_url()
    print(f"[*] Initializing schema on {db_url}...")
    engine = create_async_engine(db_url, echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    await engine.dispose()
    print("[OK] Schema created successfully.")

if __name__ == "__main__":
    asyncio.run(init_db())
