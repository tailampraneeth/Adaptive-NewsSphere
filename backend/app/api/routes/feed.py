import uuid
from datetime import datetime, timezone
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.database.connection import get_db
from app.database.models.user import User
from app.database.models.story import Story
from app.database.models.article import Article
from app.database.models.reading_history import ReadingHistory
from app.api.schemas.feed import FeedResponse, FeedItem, InteractionPayload
from app.services.recommender import HeimdallRecommender, ScoredStory
from app.api.dependencies import get_current_user

router = APIRouter(prefix="/api/v1/feed", tags=["Feed"])


def map_verification_badge(story: Story) -> dict:
    """Derives a user-friendly verification status tag from publisher diversity and scores."""
    source_count = story.publisher_diversity
    score = story.verification_score or 0.0
    age_hours = 0.0
    if story.first_reported_at:
        # Keep timezone-aware subtraction
        first_reported = story.first_reported_at
        if first_reported.tzinfo is None:
            first_reported = first_reported.replace(tzinfo=timezone.utc)
        age_hours = (datetime.now(timezone.utc) - first_reported).total_seconds() / 3600.0

    if source_count >= 3 and score >= 0.70:
        return {"label": "Verified by multiple trusted sources", "color": "green", "icon": "✓"}
    elif source_count >= 2:
        return {"label": f"Confirmed by {source_count} sources", "color": "blue", "icon": "◎"}
    elif story.has_conflicts:
        return {"label": "Sources reporting conflicting details", "color": "orange", "icon": "⚠"}
    elif age_hours <= 2 and age_hours > 0:
        return {"label": "Developing story", "color": "amber", "icon": "◐"}
    elif story.last_updated_at and story.first_reported_at and story.last_updated_at > story.first_reported_at:
        return {"label": "Recently updated", "color": "blue", "icon": "↻"}
    else:
        return {"label": "Reported by a single source", "color": "gray", "icon": "●"}


def get_story_image_url(story: Story) -> Optional[str]:
    """Finds a cover image from the representative article or member articles."""
    if story.representative_article and story.representative_article.image_url:
        return story.representative_article.image_url
    for art in story.articles:
        if art.image_url:
            return art.image_url
    return None


@router.get("", response_model=FeedResponse)
async def get_personalized_feed(
    cursor: Optional[str] = None,
    limit: int = 20,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Retrieves the personalized feed for the authenticated user."""
    recommender = HeimdallRecommender(db)
    scored_stories, next_cursor = await recommender.get_feed(current_user, cursor=cursor, limit=limit)

    results = []
    for ss in scored_stories:
        badge = map_verification_badge(ss.story)
        img_url = get_story_image_url(ss.story)
        # Ensure fallback for fields that might be None
        updated_at = ss.story.last_updated_at or ss.story.created_at
        if updated_at.tzinfo is None:
            updated_at = updated_at.replace(tzinfo=timezone.utc)

        results.append(
            FeedItem(
                story_id=ss.story.id,
                title=ss.story.title or "Untitled News Update",
                summary=ss.story.summary or "Summary pending.",
                predicted_category=ss.story.predicted_category or "World",
                importance_score=ss.story.importance_score,
                trending_score=ss.story.trending_score,
                last_updated_at=updated_at,
                publisher_diversity=ss.story.publisher_diversity,
                article_count=ss.story.article_count,
                has_conflicts=ss.story.has_conflicts,
                explanation=ss.explanation,
                score=ss.score,
                verification_label=badge["label"],
                verification_color=badge["color"],
                verification_icon=badge["icon"],
                image_url=img_url
            )
        )
    return FeedResponse(results=results, next_cursor=next_cursor)


@router.get("/trending", response_model=FeedResponse)
async def get_trending_feed(
    cursor: Optional[str] = None,
    limit: int = 20,
    db: AsyncSession = Depends(get_db)
):
    """Retrieves the public global trending feed (requires no authentication)."""
    # Fetch stories order by trending_score
    from sqlalchemy.orm import selectinload
    stmt = (
        select(Story)
        .options(selectinload(Story.articles).selectinload(Article.publisher))
        .where(Story.status == "ACTIVE")
    )
    if cursor:
        try:
            cursor_time = datetime.fromisoformat(cursor)
            stmt = stmt.where(Story.last_updated_at < cursor_time)
        except Exception:
            pass

    stmt = stmt.order_by(Story.trending_score.desc(), Story.last_updated_at.desc()).limit(limit)
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
                explanation="Global trending story",
                score=s.trending_score,
                verification_label=badge["label"],
                verification_color=badge["color"],
                verification_icon=badge["icon"],
                image_url=img_url
            )
        )
    next_cursor = stories[-1].last_updated_at.isoformat() if stories else None
    return FeedResponse(results=results, next_cursor=next_cursor)


@router.post("/interact", status_code=status.HTTP_200_OK)
async def record_interaction(
    payload: InteractionPayload,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Records user reading history/interactions for personalization feedback loop."""
    story_check = await db.execute(select(Story).where(Story.id == payload.story_id))
    story = story_check.scalar_one_or_none()
    if not story:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Story not found")

    # Increment story view count if they open it
    if payload.interaction_type == "read":
        story.view_count += 1

    # Check for existing interaction to update, otherwise insert
    hist_stmt = select(ReadingHistory).where(
        ReadingHistory.user_id == current_user.id,
        ReadingHistory.story_id == payload.story_id
    )
    hist_res = await db.execute(hist_stmt)
    history = hist_res.scalar_one_or_none()

    if history:
        history.read_pct = max(history.read_pct, payload.read_pct)
        history.dwell_seconds = max(history.dwell_seconds, payload.dwell_seconds)
        history.interaction_type = payload.interaction_type
    else:
        history = ReadingHistory(
            user_id=current_user.id,
            story_id=payload.story_id,
            read_pct=payload.read_pct,
            dwell_seconds=payload.dwell_seconds,
            interaction_type=payload.interaction_type
        )
        db.add(history)

    await db.commit()
    return {"status": "success"}
