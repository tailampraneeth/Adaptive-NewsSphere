from typing import Optional, List
from datetime import timezone
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload
from sqlalchemy import func, and_

from app.database.connection import get_db
from app.database.models.story import Story
from app.database.models.article import Article
from app.api.schemas.feed import FeedResponse, FeedItem
from app.api.routes.feed import map_verification_badge, get_story_image_url

router = APIRouter(prefix="/api/v1/search", tags=["Search"])


@router.get("", response_model=FeedResponse)
async def search_stories(
    q: str,
    category: Optional[str] = None,
    publisher: Optional[str] = None,
    region: Optional[str] = None,
    sort: Optional[str] = "relevance",  # relevance | newest
    db: AsyncSession = Depends(get_db)
):
    """Performs PostgreSQL Full-Text Search on stories with metadata filters and relevance/recency sorting."""
    if not q or not q.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Search query 'q' must not be empty."
        )

    # Check if we are running in SQLite
    is_sqlite = db.bind.dialect.name == "sqlite"

    if is_sqlite:
        stmt = (
            select(Story)
            .options(selectinload(Story.articles).selectinload(Article.publisher))
            .where(Story.status == "ACTIVE")
            .where(
                and_(
                    Story.title.ilike(f"%{q}%") | Story.summary.ilike(f"%{q}%")
                )
            )
        )
        if category:
            stmt = stmt.where(Story.predicted_category == category)
        if publisher:
            stmt = stmt.join(Article, Article.story_id == Story.id).where(Article.publisher_id == publisher)
        if region:
            from sqlalchemy import String, cast
            stmt = stmt.where(cast(Story.region_tags, String).contains(region))
        if sort == "newest":
            stmt = stmt.order_by(Story.first_reported_at.desc())
        else:
            stmt = stmt.order_by(Story.trending_score.desc())
        stmt = stmt.limit(50)
        res = await db.execute(stmt)
        stories = res.scalars().all()
    else:
        ts_query = func.plainto_tsquery("english", q)
        stmt = (
            select(Story)
            .options(selectinload(Story.articles).selectinload(Article.publisher))
            .where(Story.status == "ACTIVE")
            .where(Story.search_vector.op("@@")(ts_query))
        )

        if category:
            stmt = stmt.where(Story.predicted_category == category)
        if publisher:
            stmt = stmt.join(Article, Article.story_id == Story.id).where(Article.publisher_id == publisher)
        if region:
            from sqlalchemy import String, cast
            stmt = stmt.where(cast(Story.region_tags, String).contains(region))

        # Rank sorting
        rank_func = func.ts_rank(Story.search_vector, ts_query)
        if sort == "newest":
            stmt = stmt.order_by(Story.first_reported_at.desc())
        else:
            stmt = stmt.order_by(rank_func.desc())

        # Limit to 50 results
        stmt = stmt.limit(50)
        res = await db.execute(stmt)
        stories = res.scalars().all()

    results = []
    for s in stories:
        badge = map_verification_badge(s)
        img_url = get_story_image_url(s)
        updated_at = s.last_updated_at or s.created_at
        if updated_at.tzinfo is None:
            updated_at = updated_at.replace(tzinfo=timezone.utc)

        results.append(
            FeedItem(
                story_id=s.id,
                title=s.title or "Untitled News Update",
                summary=s.summary or "Summary pending.",
                predicted_category=s.predicted_category or "World",
                importance_score=s.importance_score,
                trending_score=s.trending_score,
                last_updated_at=updated_at,
                publisher_diversity=s.publisher_diversity,
                article_count=s.article_count,
                has_conflicts=s.has_conflicts,
                explanation="FTS search match",
                score=1.0,
                verification_label=badge["label"],
                verification_color=badge["color"],
                verification_icon=badge["icon"],
                image_url=img_url
            )
        )
    return FeedResponse(results=results, next_cursor=None)
