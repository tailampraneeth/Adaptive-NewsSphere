import asyncio
import sys
import os
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from sqlalchemy.future import select

# Add backend to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from app.core.config import settings
from app.database.models.publisher import Publisher
from app.services.ingestion import IngestionService

# Expanded list of 12 trusted RSS news sources with additional sub-categories to reach 500-1000 articles
NEWS_FEEDS = [
    {
        "id": "bbc",
        "name": "BBC News",
        "base_url": "https://www.bbc.com",
        "feed_url": "http://feeds.bbci.co.uk/news/rss.xml"
    },
    {
        "id": "bbc",
        "name": "BBC News",
        "base_url": "https://www.bbc.com",
        "feed_url": "http://feeds.bbci.co.uk/news/technology/rss.xml"
    },
    {
        "id": "bbc",
        "name": "BBC News",
        "base_url": "https://www.bbc.com",
        "feed_url": "http://feeds.bbci.co.uk/news/business/rss.xml"
    },
    {
        "id": "reuters",
        "name": "Reuters News",
        "base_url": "https://www.reuters.com",
        "feed_url": "https://news.google.com/rss/search?q=site:reuters.com&hl=en-US"
    },
    {
        "id": "ap",
        "name": "Associated Press",
        "base_url": "https://apnews.com",
        "feed_url": "https://news.google.com/rss/search?q=site:apnews.com&hl=en-US"
    },
    {
        "id": "techcrunch",
        "name": "TechCrunch",
        "base_url": "https://techcrunch.com",
        "feed_url": "https://techcrunch.com/feed/"
    },
    {
        "id": "thehindu",
        "name": "The Hindu",
        "base_url": "https://www.thehindu.com",
        "feed_url": "https://www.thehindu.com/feeder/default.rss"
    },
    {
        "id": "cnbc",
        "name": "CNBC",
        "base_url": "https://www.cnbc.com",
        "feed_url": "https://www.cnbc.com/id/100003114/device/rss/rss.xml"
    },
    {
        "id": "mit_tech_review",
        "name": "MIT Technology Review",
        "base_url": "https://www.technologyreview.com",
        "feed_url": "https://www.technologyreview.com/feed/"
    },
    {
        "id": "arstechnica",
        "name": "Ars Technica",
        "base_url": "https://arstechnica.com",
        "feed_url": "https://feeds.feedburner.com/arstechnica/index"
    },
    {
        "id": "wired",
        "name": "Wired",
        "base_url": "https://www.wired.com",
        "feed_url": "https://www.wired.com/feed/rss"
    },
    {
        "id": "theverge",
        "name": "The Verge",
        "base_url": "https://www.theverge.com",
        "feed_url": "https://www.theverge.com/rss/index.xml"
    },
    {
        "id": "guardian",
        "name": "The Guardian",
        "base_url": "https://www.theguardian.com",
        "feed_url": "https://www.theguardian.com/international/rss"
    },
    {
        "id": "techradar",
        "name": "TechRadar",
        "base_url": "https://www.techradar.com",
        "feed_url": "https://www.techradar.com/rss"
    }
]

async def collect_news():
    db_url = settings.get_database_url()
    print("=" * 60)
    print("      ADAPTIVE NEWSSPHERE: MASS NEWS INGESTION CRAWLER")
    print("=" * 60)
    print(f"Connecting to database: {db_url.split('@')[-1]}")
    
    engine = create_async_engine(db_url, echo=False)
    async_session = async_sessionmaker(bind=engine, expire_on_commit=False)
    
    overall_stats = {
        "inserted": 0,
        "skipped_duplicate": 0,
        "errors": 0
    }
    
    async with async_session() as session:
        service = IngestionService(session)
        
        # 1. Register all publishers first
        print("\n[*] Registering news publishers...")
        for feed in NEWS_FEEDS:
            # Check if publisher exists
            res = await session.execute(select(Publisher).filter_by(id=feed["id"]))
            pub = res.scalar_one_or_none()
            if not pub:
                new_pub = Publisher(
                    id=feed["id"],
                    name=feed["name"],
                    base_url=feed["base_url"],
                    credibility_score=0.90,
                    bias_rating="center"
                )
                session.add(new_pub)
                print(f"  [+] Registered: {feed['name']} (ID: {feed['id']})")
        await session.commit()
        
        # 2. Ingest articles from each feed
        print("\n[*] Starting ingestion sequence...")
        for feed in NEWS_FEEDS:
            print(f"  -> Ingesting feed: {feed['name']} ({feed['feed_url']})...")
            try:
                stats = await service.ingest_feed(feed["id"], feed["feed_url"])
                print(f"     [OK] Inserted: {stats['inserted']} | Skipped: {stats['skipped_duplicate']} | Errors: {stats['errors']}")
                
                overall_stats["inserted"] += stats["inserted"]
                overall_stats["skipped_duplicate"] += stats["skipped_duplicate"]
                overall_stats["errors"] += stats["errors"]
            except Exception as e:
                print(f"     [ERROR] Ingestion failed for {feed['name']}: {e}")
                overall_stats["errors"] += 1
                
    print("=" * 60)
    print("                      CRAWL STATISTICS")
    print("=" * 60)
    print(f"  Total Articles Inserted   : {overall_stats['inserted']}")
    print(f"  Total Duplicates Skipped  : {overall_stats['skipped_duplicate']}")
    print(f"  Total Failed Operations   : {overall_stats['errors']}")
    print("=" * 60)
    
    await engine.dispose()

if __name__ == "__main__":
    asyncio.run(collect_news())
