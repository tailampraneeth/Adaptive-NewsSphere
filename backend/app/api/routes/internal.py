import hmac
import logging
from typing import Optional
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, Header, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload

from app.core.config import settings
from app.database.connection import get_db
from app.database.models.publisher import Publisher
from app.database.models.story import Story
from app.database.models.article import Article
from app.services.ingestion import IngestionService
from app.services.story_verification import StoryVerificationService
from app.services.summarizer import StorySummarizerService

logger = logging.getLogger("heimdall.internal_routes")
router = APIRouter(prefix="/api/v1/internal", tags=["Internal"])


def verify_secret(x_ingest_secret: Optional[str] = Header(None, alias="X-Ingest-Secret")):
    """Constant-time validation of ingestion webhook secret header."""
    if not x_ingest_secret:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Header 'X-Ingest-Secret' missing."
        )
    if not hmac.compare_digest(x_ingest_secret, settings.INGEST_SECRET):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid ingest secret."
        )
    return True


@router.post("/ingest", dependencies=[Depends(verify_secret)])
async def trigger_ingest(db: AsyncSession = Depends(get_db)):
    """Triggers batch RSS feed parsing across all registered publishers and runs verification."""
    logger.info("Batch RSS Ingestion triggered via internal endpoint.")
    
    # Fetch all publishers
    res = await db.execute(select(Publisher))
    publishers = res.scalars().all()
    
    if not publishers:
        return {"status": "success", "message": "No publishers registered to ingest."}

    ingest_service = IngestionService(db)
    verification_service = StoryVerificationService(db)
    
    summary_stats = {}
    updated_stories_ids = set()

    for pub in publishers:
        try:
            stats = await ingest_service.ingest_feed(pub.id, pub.rss_url)
            summary_stats[pub.id] = stats
            
            # Find stories updated or created in this run
            # We can find articles inserted in the last hour
            from datetime import timedelta
            recent_bound = datetime.now(timezone.utc) - timedelta(hours=1)
            art_stmt = select(Article.story_id).where(
                Article.publisher_id == pub.id,
                Article.created_at >= recent_bound
            )
            art_res = await db.execute(art_stmt)
            story_ids = {row[0] for row in art_res.all() if row[0]}
            updated_stories_ids.update(story_ids)
        except Exception as pe:
            logger.error(f"Feed ingestion error for {pub.id}: {pe}")
            summary_stats[pub.id] = {"error": str(pe)}

    # Trigger Story verification/timelines for updated stories
    verified_count = 0
    for sid in updated_stories_ids:
        try:
            await verification_service.verify_story(sid)
            verified_count += 1
        except Exception as ve:
            logger.error(f"Verification engine failed for story {sid}: {ve}")

    return {
        "status": "success",
        "publishers_processed": len(publishers),
        "stories_verified": verified_count,
        "details": summary_stats
    }


@router.post("/summarize", dependencies=[Depends(verify_secret)])
async def trigger_summarize(db: AsyncSession = Depends(get_db)):
    """Generates AI summaries for stories lacking one using Gemini."""
    logger.info("Batch AI Summarization triggered via internal endpoint.")

    # Find active stories without AI summaries
    stmt = (
        select(Story)
        .options(selectinload(Story.articles))
        .where(Story.status == "ACTIVE")
        .where(Story.ai_summary.is_(None))
        .order_by(Story.last_updated_at.desc())
        .limit(30)  # Safe batch limit to protect free tier Gemini API quotas
    )
    res = await db.execute(stmt)
    stories = res.scalars().all()

    if not stories:
        return {"status": "success", "message": "No pending summaries to generate."}

    summarizer = StorySummarizerService()
    success_count = 0

    for story in stories:
        # Find the longest article to use as summary source context
        longest_article = None
        longest_len = 0
        for art in story.articles:
            body_len = len(art.body_text or "")
            if body_len > longest_len:
                longest_len = body_len
                longest_article = art

        if not longest_article:
            continue

        try:
            summary_md = await summarizer.summarize_story(story, longest_article.body_text)
            if summary_md:
                story.ai_summary = summary_md
                story.ai_summary_at = datetime.now(timezone.utc)
                success_count += 1
        except Exception as se:
            logger.error(f"Gemini summary generation failed for story {story.id}: {se}")

    await db.commit()
    return {
        "status": "success",
        "attempted": len(stories),
        "summarized": success_count
    }
