import uuid
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload
from app.database.connection import get_db
from app.database.models.story import Story
from app.database.models.article import Article
from app.api.schemas.stories import StoryDetailResponse

router = APIRouter(prefix="/api/v1/stories", tags=["Stories"])


@router.get("/{story_id}", response_model=StoryDetailResponse)
async def get_story_details(story_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    """
    Retrieves full story cluster metadata, including all source articles,
    chronological milestones, and self-referencing related stories.
    """
    stmt = (
        select(Story)
        .options(
            selectinload(Story.articles).selectinload(Article.publisher),
            selectinload(Story.timelines),
            selectinload(Story.related_stories)
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

    # Format the nested models manually if needed, or rely on pydantic from_attributes.
    # Pydantic is configured with from_attributes=True, so it will serialize the
    # lists automatically!
    
    # We do need to handle the fields that pydantic maps (e.g. publisher_name is mapped
    # from article.publisher.name, credibility_score is mapped from article.publisher.credibility_score).
    # Since ArticleSourceItem expects publisher_name and credibility_score directly,
    # let's pre-process the articles list to match the schema exactly.
    articles_data = []
    for art in story.articles:
        articles_data.append({
            "id": art.id,
            "title": art.title,
            "publish_date": art.published_at,
            "source_url": art.source_url,
            "author": art.author,
            "publisher_name": art.publisher.name if art.publisher else "Unknown",
            "credibility_score": art.publisher.credibility_score if art.publisher else 0.50,
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
    for rs in story.related_stories:
        related_data.append({
            "id": rs.id,
            "title": rs.title,
            "importance_score": rs.importance_score,
            "trending_score": rs.trending_score
        })
        
    return {
        "id": story.id,
        "title": story.title,
        "summary": story.summary,
        "summary_quick": story.summary_quick,
        "summary_beginner": story.summary_beginner,
        "summary_professional": story.summary_professional,
        "importance_score": story.importance_score,
        "trending_score": story.trending_score,
        "credibility_score": story.credibility_score,
        "verification_score": story.verification_score,
        "has_conflicts": story.has_conflicts,
        "publisher_diversity": story.publisher_diversity,
        "article_count": story.article_count,
        "last_updated_at": story.last_updated_at or story.updated_at,
        "articles": articles_data,
        "timelines": timelines_data,
        "related_stories": related_data,
        "evidence": story.evidence,
        "verification_metadata": story.verification_metadata
    }
