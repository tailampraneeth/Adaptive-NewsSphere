import asyncio
import os
import sys
import uuid
from datetime import datetime, timezone, timedelta
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.config import settings
from app.database.models.story import Story, StoryRelation
from app.database.models.article import Article
from app.database.models.publisher import Publisher
from app.database.models.timeline import StoryTimeline

STORIES_DATA = [
    {
        "title": "Google launches Gemini 2.0 Flash with Ultra-low Latency",
        "category": "Technology",
        "region": ["US", "India"],
        "summary": "Google has announced the release of its new Gemini 2.0 Flash model, optimizing prompt speed.",
        "ai_summary": """
## Main Event
Google released its latest Gemini 2.0 Flash model, focusing on speed and cost reduction.
## Background
Large language models have historically suffered from slow output generation, which is a blocker for real-time applications.
## Timeline
- Google announces Gemini 2.0 Flash project.
- Initial API beta rolled out to select enterprise developers.
- Public release across all Google AI Studio tiers.
## Key People & Organizations
Google DeepMind, Sundar Pichai.
## Impact
Developers can build faster real-time conversational agents at 50% lower cost.
## Why It Matters
This represents a significant milestone in lowering latency and cost for conversational intelligence.
## Key Takeaways
- Gemini 2.0 Flash is 3x faster than previous models.
- API is available immediately on the free tier.
- Lowers token execution costs by half.
""",
        "articles": [
            {
                "title": "Google DeepMind unveils Gemini 2.0 Flash",
                "body": "Google DeepMind announced Gemini 2.0 Flash today, featuring ultra-low latency.",
                "url": "https://www.bbc.com/news/technology",
                "pub": "bbc",
                "hash": "hash_g1"
            },
            {
                "title": "Inside Gemini 2.0 Flash launch",
                "body": "Google deepens its AI speed dominance with Gemini 2.0 Flash rollout.",
                "url": "https://techcrunch.com/",
                "pub": "techcrunch",
                "hash": "hash_g2"
            }
        ]
    },
    {
        "title": "SpaceX Starship Completes Flight 5 with Booster Catch",
        "category": "Science",
        "region": ["US"],
        "summary": "SpaceX successfully launched Starship Flight 5 and caught the Super Heavy booster.",
        "ai_summary": """
## Main Event
SpaceX successfully completed Flight 5 of Starship, catching the giant booster at the launchpad.
## Background
Reusable rockets are critical for scaling mars colonization and lunar landing programs.
## Timeline
- Flight 5 liftoff from Boca Chica, Texas.
- Tower arms capture the returning Super Heavy booster.
- Ship achieves orbital velocity and splashes down in Indian Ocean.
## Key People & Organizations
SpaceX, Elon Musk.
## Impact
Proves flight-capture technology is viable for rapid booster reusability.
## Why It Matters
Lowers launch costs significantly, enabling the next generation of space logistics.
## Key Takeaways
- Booster was caught using Mechazilla chopsticks.
- Ship completed a controlled reentry profile.
- Splashed down exactly in the target zone.
""",
        "articles": [
            {
                "title": "SpaceX catches giant rocket booster",
                "body": "SpaceX achieved a history-making rocket booster catch on Flight 5.",
                "url": "https://www.reuters.com/technology/",
                "pub": "reuters",
                "hash": "hash_s1"
            },
            {
                "title": "How Mechazilla caught Starship",
                "body": "Boca Chica launch pad chopsticks captured returning booster.",
                "url": "https://www.theverge.com/",
                "pub": "theverge",
                "hash": "hash_s2"
            }
        ]
    },
    {
        "title": "Global Inflation Cools down in Major Economies",
        "category": "Business",
        "region": ["India", "Germany", "United States"],
        "summary": "Inflation levels are trending downwards in major economic zones, prompting rate cuts.",
        "ai_summary": """
## Main Event
Central banks are preparing to cut interest rates as inflation numbers cool down.
## Background
Post-pandemic supply chain issues led to a multi-year high in consumer prices.
## Timeline
- US Federal Reserve signals inflation slowdown.
- ECB announces quarter-point rate reduction.
- RBI holds stance but notes cooling trend.
## Key People & Organizations
Federal Reserve, Jerome Powell, ECB.
## Impact
Cheaper borrowing costs for consumers and businesses globally.
## Why It Matters
Signals a transition from monetary tightening back to growth-oriented policies.
## Key Takeaways
- US inflation index fell to 2.5%.
- Markets reacted positively to anticipated rate cuts.
- Manufacturing costs are stabilizing.
""",
        "articles": [
            {
                "title": "Federal Reserve notes inflation cooling",
                "body": "Federal Reserve Chairman signals rate cuts are imminent as prices stabilize.",
                "url": "https://www.ft.com/",
                "pub": "ft",
                "hash": "hash_f1"
            },
            {
                "title": "ECB cuts interest rates as inflation eases",
                "body": "European Central Bank announces rate reduction amid price index normalization.",
                "url": "https://www.bloomberg.com/",
                "pub": "bloombergtech",
                "hash": "hash_f2"
            }
        ]
    }
]

async def seed_demo_stories():
    db_url = settings.get_database_url()
    print(f"[*] Connecting to database to seed demo stories...")

    engine = create_async_engine(db_url, echo=False)
    async_session = async_sessionmaker(bind=engine, expire_on_commit=False)

    async with async_session() as session:
        from sqlalchemy import select
        existing_stories = await session.execute(select(Story))
        if len(existing_stories.scalars().all()) > 0:
            print("[*] Stories already exist. Skipping seed.")
            await engine.dispose()
            return

        now = datetime.now(timezone.utc)
        for sdata in STORIES_DATA:
            story_id = uuid.uuid4()
            story = Story(
                id=story_id,
                title=sdata["title"],
                summary=sdata["summary"],
                ai_summary=sdata["ai_summary"],
                ai_summary_at=now,
                predicted_category=sdata["category"],
                region_tags=sdata["region"],
                first_reported_at=now - timedelta(hours=6),
                last_updated_at=now,
                publisher_diversity=len(sdata["articles"]),
                article_count=len(sdata["articles"]),
                importance_score=0.75,
                trending_score=0.85,
                status="ACTIVE",
                has_conflicts=False
            )
            session.add(story)

            # Add articles
            for art_data in sdata["articles"]:
                art_id = uuid.uuid4()
                article = Article(
                    id=art_id,
                    story_id=story_id,
                    publisher_id=art_data["pub"],
                    title=art_data["title"],
                    body_text=art_data["body"],
                    canonical_url=art_data["url"],
                    source_url=art_data["url"],
                    published_at=now - timedelta(hours=3),
                    content_hash=art_data["hash"] + "_content",
                    article_hash=art_data["hash"] + "_art",
                    predicted_category=sdata["category"]
                )
                session.add(article)

            # Add a timeline entry
            timeline = StoryTimeline(
                id=uuid.uuid4(),
                story_id=story_id,
                event_timestamp=now - timedelta(hours=2),
                headline=sdata["title"],
                description=sdata["summary"]
            )
            session.add(timeline)
            print(f"[+] Added story: {sdata['title']}")

        await session.commit()
    await engine.dispose()
    print("[OK] Demo stories seed completed successfully!")

if __name__ == "__main__":
    asyncio.run(seed_demo_stories())
