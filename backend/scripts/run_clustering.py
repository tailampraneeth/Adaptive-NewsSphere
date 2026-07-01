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
from app.database.models.story import Story
from app.services.embedder import EmbedderService
from app.services.vector_store import VectorStoreService
from app.services.clustering import ClusteringService

async def run_semantic_clustering():
    db_url = settings.get_database_url()
    print("=" * 60)
    print("      ADAPTIVE NEWSSPHERE: SEMANTIC STORY CLUSTERING")
    print("=" * 60)
    
    # 1. Initialize services
    embedder = EmbedderService()
    vector_store = VectorStoreService()
    
    engine = create_async_engine(db_url, echo=False)
    async_session = async_sessionmaker(bind=engine, expire_on_commit=False)
    
    async with async_session() as session:
        # 2. Get all articles with body_text that do not have a story_id
        result = await session.execute(
            select(Article).where(Article.story_id.is_(None)).order_by(Article.published_at.desc())
        )
        articles = result.scalars().all()
        total_count = len(articles)
        
        print(f"\n[*] Found {total_count} articles requiring semantic story grouping.")
        if total_count == 0:
            print("[*] No articles to cluster. Exiting.")
            await engine.dispose()
            return
            
        clustering_service = ClusteringService(session, embedder, vector_store)
        
        # Process all articles in a single run
        batch_limit = 1000
        articles_to_process = articles[:batch_limit]
        print(f"[*] Grouping batch of {len(articles_to_process)} articles...")
        
        t0 = time.time()
        processed = 0
        
        for article in articles_to_process:
            try:
                await clustering_service.cluster_article(article)
                processed += 1
                if processed % 10 == 0:
                    print(f"  [+] Clustered {processed}/{len(articles_to_process)} articles...")
            except Exception as e:
                print(f"  [!] Ingestion error on article {article.id}: {e}")
                
        # Let's count total stories in the database
        story_count_res = await session.execute(select(Story))
        stories_total = len(story_count_res.scalars().all())
        
        duration = time.time() - t0
        print("\n" + "=" * 60)
        print("                  CLUSTERING RESULTS")
        print("=" * 60)
        print(f"  Articles Processed : {processed}")
        print(f"  Total Stories      : {stories_total}")
        print(f"  Time Elapsed       : {duration:.2f} seconds")
        print("=" * 60)
        
    await engine.dispose()

if __name__ == "__main__":
    asyncio.run(run_semantic_clustering())
