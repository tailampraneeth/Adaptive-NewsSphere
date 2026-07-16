import asyncio
import sys
import os
import time
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from sqlalchemy.future import select

# Add backend to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from app.core.config import settings
from app.database.models.story import Story
from app.services.embedder import EmbedderService
from app.services.vector_store import VectorStoreService
from app.services.story_verification import StoryVerificationService

async def run_verification():
    db_url = settings.get_database_url()
    print("=" * 60)
    print("      ADAPTIVE NEWSSPHERE: STORY VERIFICATION & TIMELINE GENERATION")
    print("=" * 60)

    # 1. Initialize services
    embedder = EmbedderService()
    vector_store = VectorStoreService()

    engine = create_async_engine(db_url, echo=False)
    async_session = async_sessionmaker(bind=engine, expire_on_commit=False)

    async with async_session() as session:
        # 2. Get all stories
        result = await session.execute(select(Story).order_by(Story.created_at.desc()))
        stories = result.scalars().all()
        total_count = len(stories)

        print(f"\n[*] Found {total_count} stories requiring verification & timeline building.")
        if total_count == 0:
            print("[*] No stories found. Exiting.")
            await engine.dispose()
            return

        verifier = StoryVerificationService(session, embedder, vector_store)

        t0 = time.time()
        processed = 0

        for story in stories:
            try:
                await verifier.verify_story(story.id)
                processed += 1
                if processed % 10 == 0 or processed == total_count:
                    print(f"  [+] Verified {processed}/{total_count} stories...")
            except Exception as e:
                print(f"  [!] Error verifying story {story.id}: {e}")

        duration = time.time() - t0
        print("\n" + "=" * 60)
        print("                  VERIFICATION RESULTS")
        print("=" * 60)
        print(f"  Stories Verified : {processed}")
        print(f"  Time Elapsed     : {duration:.2f} seconds")
        print("=" * 60)

    await engine.dispose()

if __name__ == "__main__":
    asyncio.run(run_verification())
