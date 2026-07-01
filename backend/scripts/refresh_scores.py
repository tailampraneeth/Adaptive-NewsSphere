"""
refresh_scores.py — Story importance and trending score refresh.

Recalculates importance_score and trending_score for all ACTIVE stories
without requiring new article ingestion. Essential for correctly decaying
trending scores over time — a story that received no new articles should
naturally drop in the trending feed.

Design:
  - Works in batches of 100 stories to avoid memory pressure
  - Only updates ACTIVE stories (MERGED/ARCHIVED are excluded)
  - Reads articles from Postgres only (no Qdrant access needed for scoring)
  - Safe to run repeatedly; results are deterministic for the same data

Recommended cadence:
  Every 4–6 hours (e.g., via scheduled task or cron)

Usage:
  python scripts/refresh_scores.py
  python scripts/refresh_scores.py --batch-size 50
"""
import asyncio
import argparse
import math
import os
import sys
import time
from datetime import datetime, timezone
from typing import List

from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from sqlalchemy.future import select

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from app.core.config import settings
from app.database.models.article import Article
from app.database.models.story import Story


_IMPORTANCE_HALF_LIFE_H = 24.0
_TRENDING_HALF_LIFE_H = 6.0


def _decay(articles: List[Article], half_life_hours: float) -> float:
    now = datetime.now(timezone.utc)
    valid_times = []
    for a in articles:
        if a.published_at:
            ts = a.published_at
            if ts.tzinfo is None:
                ts = ts.replace(tzinfo=timezone.utc)
            valid_times.append(ts)
    if not valid_times:
        return 1.0
    newest = max(valid_times)
    age_h = max(0.0, (now - newest).total_seconds() / 3600.0)
    return math.pow(2.0, -age_h / half_life_hours)


def _compute_importance(story: Story, articles: List[Article]) -> float:
    count_score = min(1.0, story.article_count / 20.0)
    pub_div = min(1.0, len({a.publisher_id for a in articles}) / 5.0)
    freshness = _decay(articles, _IMPORTANCE_HALF_LIFE_H)
    conf = float(story.confidence_score)
    return round(min(1.0, count_score * 0.35 + pub_div * 0.35 + freshness * 0.20 + conf * 0.10), 6)


def _compute_trending(story: Story, articles: List[Article]) -> float:
    recency = _decay(articles, _TRENDING_HALF_LIFE_H)
    now = datetime.now(timezone.utc)
    recent = [
        a for a in articles
        if a.published_at and (now - a.published_at.replace(
            tzinfo=timezone.utc if a.published_at.tzinfo is None else a.published_at.tzinfo
        )).total_seconds() < 86400
    ]
    growth = min(1.0, len(recent) / 10.0)
    pub_div = min(1.0, len({a.publisher_id for a in articles}) / 5.0)
    return round(min(1.0, recency * 0.40 + growth * 0.30 + pub_div * 0.30), 6)


async def refresh_all_scores(batch_size: int = 100) -> None:
    db_url = settings.get_database_url()

    print("=" * 60)
    print("    ADAPTIVE NEWSSPHERE: SCORE REFRESH")
    print("=" * 60)
    print(f"  Batch size: {batch_size}")

    engine = create_async_engine(db_url, echo=False)
    async_session = async_sessionmaker(bind=engine, expire_on_commit=False)

    async with async_session() as session:
        res = await session.execute(
            select(Story).where(Story.status == "ACTIVE")
        )
        stories = res.scalars().all()
        total = len(stories)
        print(f"[*] Found {total} ACTIVE stories to refresh.\n")

        if total == 0:
            await engine.dispose()
            return

        t0 = time.time()
        updated = 0

        for i, story in enumerate(stories):
            try:
                arts_res = await session.execute(
                    select(Article).where(Article.story_id == story.id)
                )
                arts = list(arts_res.scalars().all())
                story.importance_score = _compute_importance(story, arts)
                story.trending_score = _compute_trending(story, arts)
                updated += 1
            except Exception as e:
                print(f"  [!] Error on Story {story.id}: {e}")

            if (i + 1) % batch_size == 0:
                await session.commit()
                print(f"  [+] Refreshed {i + 1}/{total}...")

        await session.commit()
        duration = time.time() - t0

        print()
        print("=" * 60)
        print("                REFRESH RESULTS")
        print("=" * 60)
        print(f"  Stories Updated  : {updated}/{total}")
        print(f"  Time Elapsed     : {duration:.2f}s")
        print("=" * 60)

    await engine.dispose()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Refresh story importance/trending scores")
    parser.add_argument("--batch-size", type=int, default=100)
    args = parser.parse_args()
    asyncio.run(refresh_all_scores(batch_size=args.batch_size))
