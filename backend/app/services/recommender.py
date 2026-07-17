import logging
from datetime import datetime, timezone
from typing import List, Optional, Dict, Any, Tuple
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload
from sqlalchemy import func

from app.core.config import settings
from app.database.models.user import User
from app.database.models.story import Story
from app.database.models.article import Article
from app.database.models.reading_history import ReadingHistory

logger = logging.getLogger("heimdall.recommender")


def safe_hours_old(now: datetime, dt: datetime) -> float:
    """Safely calculates the difference in hours between two datetimes, handling naive/aware differences."""
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    if now.tzinfo is None:
        now = now.replace(tzinfo=timezone.utc)
    return max(0.0, (now - dt).total_seconds() / 3600.0)



class ScoredStory:
    def __init__(self, story: Story, score: float, explanation: str):
        self.story = story
        self.score = score
        self.explanation = explanation


class HeimdallRecommender:
    """SQL-based lightweight news recommender with reading completion feedback and cold start handling."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_feed(self, user: User, cursor: Optional[str] = None, limit: int = 20) -> Tuple[List[ScoredStory], Optional[str]]:
        """
        Returns a ranked list of ScoredStory candidate feeds using cursor pagination.
        
        Returns:
            Tuple[List[ScoredStory], next_cursor_string]
        """
        now = datetime.now(timezone.utc)

        # ── Step 1: Query user's reading history for cold-start and seen exclusion ──
        history_res = await self.db.execute(
            select(ReadingHistory)
            .where(ReadingHistory.user_id == user.id)
        )
        history_records = history_res.scalars().all()
        seen_story_ids = {h.story_id for h in history_records}
        total_reads = len(history_records)

        # Calculate category performance averages for reading completion feedback
        category_perf: Dict[str, Tuple[float, int]] = {}  # category -> (avg_read_pct, count)
        for h in history_records:
            # We need to fetch story category, but since we didn't join here, let's execute a group-by query for efficiency.
            pass

        # Dedicated group-by query for category performance metrics (Polish #3 & #6)
        perf_stmt = (
            select(
                Story.predicted_category,
                func.avg(ReadingHistory.read_pct),
                func.count(ReadingHistory.id),
                func.avg(ReadingHistory.dwell_seconds)
            )
            .join(Story, ReadingHistory.story_id == Story.id)
            .where(ReadingHistory.user_id == user.id)
            .group_by(Story.predicted_category)
        )
        perf_res = await self.db.execute(perf_stmt)
        # category -> {"avg_pct": float, "count": int, "avg_dwell": float}
        user_category_metrics = {
            row[0]: {"avg_pct": float(row[1] or 0), "count": int(row[2] or 0), "avg_dwell": float(row[3] or 0)}
            for row in perf_res.all()
        }

        # ── Step 2: Fetch Story Candidates ──
        # Fetching Story + Article + Publisher eager load to eliminate N+1 queries
        stmt = (
            select(Story)
            .options(selectinload(Story.articles).selectinload(Article.publisher))
            .where(Story.status == "ACTIVE")
            .where(~Story.id.in_(seen_story_ids) if seen_story_ids else True)
        )

        # Filter hidden categories/publishers
        if user.hidden_categories:
            stmt = stmt.where(Story.predicted_category.notin_(user.hidden_categories))

        # Cursor pagination (based on last_updated_at ISO string)
        if cursor:
            try:
                cursor_time = datetime.fromisoformat(cursor)
                stmt = stmt.where(Story.last_updated_at < cursor_time)
            except Exception as ce:
                logger.warning(f"Invalid cursor format: {cursor}. Falling back to default pagination: {ce}")

        # Limit candidate pool size to prevent excessive processing
        stmt = stmt.order_by(Story.last_updated_at.desc()).limit(100)
        stories_res = await self.db.execute(stmt)
        candidates = stories_res.scalars().all()

        # ── Step 3: Handle Cold Start ──
        if total_reads < settings.COLD_START_MIN_READS:
            logger.info(f"Cold-start active for user {user.id} ({total_reads} reads). Ordering by trending score.")
            scored_candidates = []
            for s in candidates:
                # Cold start scores purely based on trending_score + freshness
                hours_old = safe_hours_old(now, s.last_updated_at)
                freshness = 2 ** (-hours_old / settings.FRESHNESS_HALF_LIFE_HOURS)
                score = (0.7 * s.trending_score) + (0.3 * freshness)
                scored_candidates.append(ScoredStory(story=s, score=score, explanation="Trending story (cold start)"))
            
            scored_candidates.sort(key=lambda x: x.score, reverse=True)
            page = scored_candidates[:limit]
            next_cursor = page[-1].story.last_updated_at.isoformat() if page else None
            return page, next_cursor

        # ── Step 4: Persona-Based Scoring ──
        scored_candidates = []
        for s in candidates:
            # 1. Interest Match (40%)
            interest = 0.0
            cat = s.predicted_category
            if cat and user.preferred_categories and cat in user.preferred_categories:
                interest = 1.0

            # Apply completion feedback adjustments
            if cat in user_category_metrics:
                metrics = user_category_metrics[cat]
                if metrics["avg_pct"] >= 70.0:
                    interest += settings.COMPLETION_BOOST
                elif metrics["count"] >= 3 and metrics["avg_pct"] <= 20.0:
                    interest -= settings.ABANDONMENT_PENALTY

            # 2. Region Match (25%)
            region_match = 0.0
            if s.region_tags and (user.country or user.state):
                user_regions = {user.country, user.state}
                story_regions = set(s.region_tags)
                if user_regions & story_regions:
                    region_match = 1.0

            # 3. Freshness (15% with 24h decay half-life)
            hours_old = safe_hours_old(now, s.last_updated_at)
            freshness = 2 ** (-hours_old / settings.FRESHNESS_HALF_LIFE_HOURS)

            # 4. Trending (10% growth view count)
            trending = s.trending_score

            # 5. Publisher Preference (10%)
            pub_match = 0.0
            if user.preferred_publishers:
                for art in s.articles:
                    if art.publisher_id in user.preferred_publishers:
                        pub_match = 1.0
                        break

            # Calculate composite score
            score = (0.40 * interest) + (0.25 * region_match) + (0.15 * freshness) + (0.10 * trending) + (0.10 * pub_match)

            # Generate explanation text
            reasons = []
            if interest > 0.5:
                reasons.append(f"you read {cat or 'this category'}")
            if region_match > 0.0:
                reasons.append(f"trending in {user.state or user.country}")
            if trending > 0.7:
                reasons.append("trending topic")
            if pub_match > 0.0:
                reasons.append("from your trusted publishers")

            explanation = ""
            if reasons:
                explanation = f"Recommended because {', '.join(reasons)}."

            scored_candidates.append(ScoredStory(story=s, score=score, explanation=explanation))

        # Sort by final score
        scored_candidates.sort(key=lambda x: x.score, reverse=True)
        page = scored_candidates[:limit]

        # Graceful fallback: Never return an empty feed if active stories exist
        if not page:
            logger.info("Personalized feed is empty. Falling back to trending/latest active stories.")
            fallback_stmt = (
                select(Story)
                .options(selectinload(Story.articles).selectinload(Article.publisher))
                .where(Story.status == "ACTIVE")
                .order_by(Story.trending_score.desc(), Story.last_updated_at.desc())
                .limit(limit)
            )
            fallback_res = await self.db.execute(fallback_stmt)
            fallback_stories = fallback_res.scalars().all()
            page = [
                ScoredStory(story=s, score=s.trending_score, explanation="Trending story (fallback)")
                for s in fallback_stories
            ]

        next_cursor = page[-1].story.last_updated_at.isoformat() if page else None
        return page, next_cursor
