import asyncio
import sys
import os
import time
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from sqlalchemy.future import select

# Add backend to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from app.core.config import settings
from app.database.models.article import Article
from app.services.nlp_processor import NLPProcessorService

async def enrich_articles():
    db_url = settings.get_database_url()
    print("=" * 60)
    print("      ADAPTIVE NEWSSPHERE: DATASET NLP ENRICHMENT")
    print("=" * 60)

    # Initialize the NLP Processor Service
    nlp_service = NLPProcessorService()

    engine = create_async_engine(db_url, echo=False)
    async_session = async_sessionmaker(bind=engine, expire_on_commit=False)

    async with async_session() as session:
        # Get all articles that do not have NLP metadata populated (e.g. keywords is null)
        result = await session.execute(
            select(Article).where(Article.keywords.is_(None)).order_by(Article.published_at.desc())
        )
        articles = result.scalars().all()
        total_count = len(articles)
        print(f"\n[*] Found {total_count} articles requiring NLP metadata enrichment.")

        if total_count == 0:
            print("[*] All articles are already enriched. Exiting.")
            await engine.dispose()
            return

        processed_count = 0
        t_start = time.time()

        # Limit batch processing to prevent taking too long in a single execution loop
        # Processing ~200 articles is a very solid, representative dataset chunk!
        batch_limit = 200
        articles_to_process = articles[:batch_limit]
        print(f"[*] Processing first batch of {len(articles_to_process)} articles...")

        for article in articles_to_process:
            try:
                # Extract NLP Metadata
                metadata = nlp_service.extract_metadata(article.title, article.body_text)

                # Update article columns
                article.named_entities = metadata["named_entities"]
                article.keywords = metadata["keywords"]
                article.topics = metadata["topics"]
                article.word_count = metadata["word_count"]
                article.character_count = metadata["character_count"]
                article.reading_time = metadata["reading_time"]

                # Set default country if not present
                if not article.country:
                    article.country = "US"

                processed_count += 1

                # Periodically commit and log progress
                if processed_count % 20 == 0:
                    await session.commit()
                    elapsed = time.time() - t_start
                    speed = processed_count / elapsed if elapsed > 0 else 0
                    print(f"  [+] Enriched {processed_count}/{len(articles_to_process)} articles... ({speed:.1f} art/sec)")
            except Exception as e:
                print(f"  [!] Failed to enrich article {article.id}: {e}")

        # Final commit for remaining articles
        await session.commit()
        t_total = time.time() - t_start
        print("\n" + "=" * 60)
        print("                 ENRICHMENT STATS")
        print("=" * 60)
        print(f"  Articles Processed : {processed_count}")
        print(f"  Total Duration     : {t_total:.2f} seconds")
        print(f"  Average Speed      : {processed_count/t_total:.2f} articles/sec" if t_total > 0 else "")
        print("=" * 60)

    await engine.dispose()

if __name__ == "__main__":
    asyncio.run(enrich_articles())
