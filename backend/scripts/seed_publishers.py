"""
Seed script for RSS Publishers (Stage 1 - 20 publishers).
"""

import asyncio
import os
import sys
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from sqlalchemy.future import select

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.config import settings
from app.database.models.publisher import Publisher, PublisherSourceType

PUBLISHERS_DATA = [
    {
        "id": "reuters",
        "name": "Reuters",
        "base_url": "https://www.reuters.com",
        "rss_url": "https://news.google.com/rss/search?q=source:Reuters&hl=en-US&gl=US&ceid=US:en",
        "credibility_score": 0.95,
        "source_type": PublisherSourceType.NEWSWIRE.value
    },
    {
        "id": "ap",
        "name": "AP News",
        "base_url": "https://apnews.com",
        "rss_url": "https://news.google.com/rss/search?q=source:%22Associated+Press%22&hl=en-US&gl=US&ceid=US:en",
        "credibility_score": 0.95,
        "source_type": PublisherSourceType.NEWSWIRE.value
    },
    {
        "id": "bbc",
        "name": "BBC News",
        "base_url": "https://www.bbc.com/news",
        "rss_url": "https://feeds.bbci.co.uk/news/rss.xml",
        "credibility_score": 0.92,
        "source_type": PublisherSourceType.INTERNATIONAL.value
    },
    {
        "id": "guardian",
        "name": "The Guardian",
        "base_url": "https://www.theguardian.com",
        "rss_url": "https://www.theguardian.com/world/rss",
        "credibility_score": 0.90,
        "source_type": PublisherSourceType.INTERNATIONAL.value
    },
    {
        "id": "aljazeera",
        "name": "Al Jazeera",
        "base_url": "https://www.aljazeera.com",
        "rss_url": "https://www.aljazeera.com/xml/rss/all.xml",
        "credibility_score": 0.88,
        "source_type": PublisherSourceType.INTERNATIONAL.value
    },
    {
        "id": "ndtv",
        "name": "NDTV",
        "base_url": "https://www.ndtv.com",
        "rss_url": "https://feeds.feedburner.com/ndtvnews-top-stories",
        "credibility_score": 0.85,
        "source_type": PublisherSourceType.LOCAL_NEWS.value
    },
    {
        "id": "thehindu",
        "name": "The Hindu",
        "base_url": "https://www.thehindu.com",
        "rss_url": "https://www.thehindu.com/news/national/feeder/default.rss",
        "credibility_score": 0.88,
        "source_type": PublisherSourceType.LOCAL_NEWS.value
    },
    {
        "id": "timesofindia",
        "name": "Times of India",
        "base_url": "https://timesofindia.indiatimes.com",
        "rss_url": "https://timesofindia.indiatimes.com/rssfeedstopstories.cms",
        "credibility_score": 0.82,
        "source_type": PublisherSourceType.LOCAL_NEWS.value
    },
    {
        "id": "npr",
        "name": "NPR",
        "base_url": "https://www.npr.org",
        "rss_url": "https://feeds.npr.org/1001/rss.xml",
        "credibility_score": 0.90,
        "source_type": PublisherSourceType.INTERNATIONAL.value
    },
    {
        "id": "theverge",
        "name": "The Verge",
        "base_url": "https://www.theverge.com",
        "rss_url": "https://www.theverge.com/rss/index.xml",
        "credibility_score": 0.88,
        "source_type": PublisherSourceType.TECH_MEDIA.value
    },
    {
        "id": "techcrunch",
        "name": "TechCrunch",
        "base_url": "https://techcrunch.com",
        "rss_url": "https://techcrunch.com/feed/",
        "credibility_score": 0.88,
        "source_type": PublisherSourceType.TECH_MEDIA.value
    },
    {
        "id": "arstechnica",
        "name": "Ars Technica",
        "base_url": "https://arstechnica.com",
        "rss_url": "https://feeds.arstechnica.com/arstechnica/index",
        "credibility_score": 0.90,
        "source_type": PublisherSourceType.TECH_MEDIA.value
    },
    {
        "id": "bloombergtech",
        "name": "Bloomberg Technology",
        "base_url": "https://www.bloomberg.com/technology",
        "rss_url": "https://news.google.com/rss/search?q=source:%22Bloomberg+Technology%22&hl=en-US&gl=US&ceid=US:en",
        "credibility_score": 0.92,
        "source_type": PublisherSourceType.FINANCIAL.value
    },
    {
        "id": "mit_tech_review",
        "name": "MIT Technology Review",
        "base_url": "https://www.technologyreview.com",
        "rss_url": "https://www.technologyreview.com/feed/",
        "credibility_score": 0.92,
        "source_type": PublisherSourceType.RESEARCH.value
    },
    {
        "id": "nature",
        "name": "Nature News",
        "base_url": "https://www.nature.com",
        "rss_url": "https://www.nature.com/nature.rss",
        "credibility_score": 0.98,
        "source_type": PublisherSourceType.RESEARCH.value
    },
    {
        "id": "sciencedaily",
        "name": "Science Daily",
        "base_url": "https://www.sciencedaily.com",
        "rss_url": "https://www.sciencedaily.com/rss/all.xml",
        "credibility_score": 0.95,
        "source_type": PublisherSourceType.RESEARCH.value
    },
    {
        "id": "espn",
        "name": "ESPN",
        "base_url": "https://www.espn.com",
        "rss_url": "https://www.espn.com/espn/rss/news",
        "credibility_score": 0.88,
        "source_type": PublisherSourceType.LOCAL_NEWS.value
    },
    {
        "id": "skysports",
        "name": "Sky Sports",
        "base_url": "https://www.skysports.com",
        "rss_url": "https://www.skysports.com/rss/12040",
        "credibility_score": 0.88,
        "source_type": PublisherSourceType.INTERNATIONAL.value
    },
    {
        "id": "ft",
        "name": "Financial Times",
        "base_url": "https://www.ft.com",
        "rss_url": "https://www.ft.com/?format=rss",
        "credibility_score": 0.92,
        "source_type": PublisherSourceType.FINANCIAL.value
    },
    {
        "id": "economist",
        "name": "The Economist",
        "base_url": "https://www.economist.com",
        "rss_url": "https://www.economist.com/sections/science-technology/rss.xml",
        "credibility_score": 0.92,
        "source_type": PublisherSourceType.FINANCIAL.value
    }
]


async def seed_publishers():
    db_url = settings.get_database_url()
    print("[*] Seeding Stage 1 Publishers...")

    engine = create_async_engine(db_url, echo=False)
    async_session = async_sessionmaker(bind=engine, expire_on_commit=False)

    async with async_session() as session:
        for pdata in PUBLISHERS_DATA:
            stmt = select(Publisher).where(Publisher.id == pdata["id"])
            res = await session.execute(stmt)
            pub = res.scalar_one_or_none()

            if not pub:
                pub = Publisher(
                    id=pdata["id"],
                    name=pdata["name"],
                    base_url=pdata["base_url"],
                    rss_url=pdata["rss_url"],
                    credibility_score=pdata["credibility_score"],
                    source_type=pdata["source_type"],
                    successful_fetches=0,
                    failed_fetches=0
                )
                session.add(pub)
                print(f"[+] Seeded: {pdata['name']}")
            else:
                pub.rss_url = pdata["rss_url"]
                pub.base_url = pdata["base_url"]
                pub.credibility_score = pdata["credibility_score"]
                pub.source_type = pdata["source_type"]
                print(f"[*] Updated: {pdata['name']}")

        await session.commit()
    await engine.dispose()
    print("[OK] Publishers seeding completed successfully!")


if __name__ == "__main__":
    asyncio.run(seed_publishers())
