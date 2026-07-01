import asyncio
import sys
import os
import time
import datetime
import feedparser
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from sqlalchemy.future import select

# Add backend to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from app.core.config import settings
from app.database.models.publisher import Publisher
from app.database.models.article import Article

# List of publisher feeds to track
CRAWL_FEEDS = {
    "bbc": "http://feeds.bbci.co.uk/news/rss.xml",
    "reuters": "https://news.google.com/rss/search?q=site:reuters.com&hl=en-US",
    "ap": "https://news.google.com/rss/search?q=site:apnews.com&hl=en-US",
    "techcrunch": "https://techcrunch.com/feed/",
    "thehindu": "https://www.thehindu.com/feeder/default.rss",
    "cnbc": "https://www.cnbc.com/id/100003114/device/rss/rss.xml",
    "mit_tech_review": "https://www.technologyreview.com/feed/",
    "arstechnica": "https://feeds.feedburner.com/arstechnica/index",
    "wired": "https://www.wired.com/feed/rss",
    "theverge": "https://www.theverge.com/rss/index.xml",
    "guardian": "https://www.theguardian.com/international/rss",
    "techradar": "https://www.techradar.com/rss"
}

async def track_feed_health():
    db_url = settings.get_database_url()
    print("=" * 60)
    print("      ADAPTIVE NEWSSPHERE: FEED HEALTH MONITOR")
    print("=" * 60)
    
    engine = create_async_engine(db_url, echo=False)
    async_session = async_sessionmaker(bind=engine, expire_on_commit=False)
    
    async with async_session() as session:
        # Fetch registered publishers
        result = await session.execute(select(Publisher))
        publishers = result.scalars().all()
        
        print(f"[*] Analyzing live feed performance for {len(publishers)} publishers...")
        
        for pub in publishers:
            feed_url = CRAWL_FEEDS.get(pub.id)
            if not feed_url:
                continue
                
            print(f"\n[*] Testing {pub.name} ({pub.id})...")
            
            # Start timer
            t0 = time.time()
            articles_count = 0
            duplicates_count = 0
            
            try:
                # 1. Parse feed and measure network latency
                feed = feedparser.parse(feed_url)
                latency_ms = (time.time() - t0) * 1000
                
                # Check for parsing errors
                if hasattr(feed, "bozo") and feed.bozo and isinstance(feed.bozo_exception, Exception):
                    raise feed.bozo_exception
                    
                entries = feed.get("entries", [])
                articles_count = len(entries)
                
                # 2. Check duplicate counts against database
                if articles_count > 0:
                    for entry in entries:
                        url = entry.get("link")
                        if url:
                            res = await session.execute(select(Article).filter_by(source_url=url))
                            if res.scalar_one_or_none():
                                duplicates_count += 1
                                
                duplicate_pct = (duplicates_count / articles_count * 100) if articles_count > 0 else 0.0
                
                # Update metrics
                pub.successful_fetches = (pub.successful_fetches or 0) + 1
                
                # Compute moving average of latency
                prev_avg = pub.avg_latency_ms or 0.0
                prev_count = max(0, pub.successful_fetches - 1)
                pub.avg_latency_ms = ((prev_avg * prev_count) + latency_ms) / pub.successful_fetches
                
                pub.articles_per_fetch = articles_count
                pub.duplicate_percentage = duplicate_pct
                pub.last_fetched_at = datetime.datetime.now(datetime.timezone.utc)
                
                print(f"    [OK] Latency: {latency_ms:.1f}ms | Articles: {articles_count} | Duplicates: {duplicate_pct:.1f}%")
            except Exception as e:
                print(f"    [FAIL] Fetch failed: {e}")
                pub.failed_fetches = (pub.failed_fetches or 0) + 1
                
        await session.commit()
        print("\n" + "=" * 60)
        print("[STATUS] Publisher health metrics updated successfully.")
        print("=" * 60)
        
    await engine.dispose()

if __name__ == "__main__":
    asyncio.run(track_feed_health())
