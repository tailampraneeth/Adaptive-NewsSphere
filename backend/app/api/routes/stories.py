import uuid
from datetime import datetime, timezone, timedelta
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload

from app.database.connection import get_db
from app.database.models.story import Story
from app.database.models.article import Article
from app.api.schemas.stories import StoryDetailResponse, RelatedStoryItem
from app.api.routes.feed import get_story_image_url

router = APIRouter(prefix="/api/v1/stories", tags=["Stories"])


@router.get("/{story_id}", response_model=StoryDetailResponse)
async def get_story_details(story_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    """Retrieves full story cluster metadata, source articles, timelines, and related stories."""
    stmt = (
        select(Story)
        .options(
            selectinload(Story.articles).selectinload(Article.publisher),
            selectinload(Story.timelines)
        )
        .where(Story.id == story_id)
    )
    result = await db.execute(stmt)
    story = result.scalar_one_or_none()
    
    if not story:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Story cluster with ID {story_id} not found."
        )

    # ── Fetch Related Stories (same category, last 48h) ──
    boundary_time = (story.first_reported_at or story.created_at) - timedelta(hours=48)
    related_stmt = (
        select(Story)
        .options(selectinload(Story.articles))
        .where(Story.predicted_category == story.predicted_category)
        .where(Story.id != story.id)
        .where(Story.status == "ACTIVE")
        .where(Story.first_reported_at >= boundary_time)
        .order_by(Story.importance_score.desc())
        .limit(6)
    )
    related_res = await db.execute(related_stmt)
    related_stories_list = related_res.scalars().all()

    articles_data = []
    for art in story.articles:
        articles_data.append({
            "id": art.id,
            "title": art.title,
            "publish_date": art.published_at,
            "source_url": art.source_url,
            "canonical_url": art.canonical_url,
            "author": art.author,
            "publisher_name": art.publisher.name if art.publisher else "Unknown",
            "credibility_score": float(art.publisher.credibility_score) if art.publisher else 0.50,
            "body_text": art.body_text,
        })
        
    timelines_data = []
    for tl in story.timelines:
        timelines_data.append({
            "id": tl.id,
            "event_timestamp": tl.event_timestamp,
            "headline": tl.headline,
            "description": tl.description,
            "importance_weight": tl.confidence_score,
            "event_type": tl.event_type
        })
        
    related_data = []
    for rs in related_stories_list:
        related_data.append({
            "id": rs.id,
            "title": rs.title,
            "importance_score": rs.importance_score,
            "trending_score": rs.trending_score,
            "predicted_category": rs.predicted_category or "General",
            "last_updated_at": rs.last_updated_at or rs.created_at,
            "image_url": get_story_image_url(rs)
        })
        
    return {
        "id": story.id,
        "title": story.title,
        "summary": story.summary,
        "ai_summary": story.ai_summary,
        "ai_summary_at": story.ai_summary_at,
        "importance_score": story.importance_score,
        "trending_score": story.trending_score,
        "credibility_score": story.credibility_score,
        "verification_score": story.verification_score,
        "has_conflicts": story.has_conflicts,
        "publisher_diversity": story.publisher_diversity,
        "article_count": story.article_count,
        "last_updated_at": story.last_updated_at or story.updated_at,
        "region_tags": story.region_tags or [],
        "articles": articles_data,
        "timelines": timelines_data,
        "related_stories": related_data,
        "evidence": story.evidence,
        "verification_metadata": story.verification_metadata
    }


@router.get("/{story_id}/related", response_model=List[RelatedStoryItem])
async def get_related_stories(story_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    """Exposes related stories via a separate REST endpoint."""
    stmt = select(Story).where(Story.id == story_id)
    res = await db.execute(stmt)
    story = res.scalar_one_or_none()
    if not story:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Story not found")

    boundary_time = (story.first_reported_at or story.created_at) - timedelta(hours=48)
    related_stmt = (
        select(Story)
        .options(selectinload(Story.articles))
        .where(Story.predicted_category == story.predicted_category)
        .where(Story.id != story.id)
        .where(Story.status == "ACTIVE")
        .where(Story.first_reported_at >= boundary_time)
        .order_by(Story.importance_score.desc())
        .limit(6)
    )
    related_res = await db.execute(related_stmt)
    related_stories_list = related_res.scalars().all()

    results = []
    for rs in related_stories_list:
        results.append(
            RelatedStoryItem(
                id=rs.id,
                title=rs.title or "Untitled News Update",
                importance_score=rs.importance_score,
                trending_score=rs.trending_score,
                predicted_category=rs.predicted_category or "World",
                last_updated_at=rs.last_updated_at or rs.created_at,
                image_url=get_story_image_url(rs)
            )
        )
    return results
