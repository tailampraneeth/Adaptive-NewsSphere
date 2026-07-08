"""
PreferenceUpdateWorker — Milestone 4: Recommendation Engine.

Processes user interaction events asynchronously to update preference vectors.

Responsibilities:
  1. Resolve article_id → story_id (via DB join)
  2. Handle mute-type interactions (update muted lists in UserProfile)
  3. Call PreferenceEngineService.update_preference_vector()
  4. Record the interaction in UserInteraction table

This worker is called from the POST /api/v1/feed/interact endpoint.
In a production system, this would be dispatched to a Celery/ARQ queue.
For the local-first architecture, it runs as an async background task
using FastAPI's BackgroundTasks.
"""
import logging
import uuid

import redis.asyncio as aioredis
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.core.config import settings
from app.database.models.article import Article
from app.database.models.interaction import UserInteraction
from app.services.preference_engine import PreferenceEngineService
from app.services.vector_store import VectorStoreService

logger = logging.getLogger("adaptive-newssphere.preference_worker")


class PreferenceUpdateWorker:
    """
    Handles the full interaction processing pipeline:
      1. Resolve article → story
      2. Handle negative feedback mutes
      3. Update preference vector via EMA
      4. Persist interaction record
    """

    def __init__(
        self,
        db_session: AsyncSession,
        vector_store: VectorStoreService,
        redis_client: aioredis.Redis,
    ) -> None:
        self.db = db_session
        self.vector_store = vector_store
        self.redis = redis_client
        self.preference_engine = PreferenceEngineService(
            db_session=db_session,
            vector_store=vector_store,
            redis_client=redis_client,
        )

    async def process_interaction(
        self,
        user_id: uuid.UUID,
        article_id: uuid.UUID,
        interaction_type: str,
        dwell_seconds: int = 0,
        category: str | None = None,
        publisher_id: str | None = None,
    ) -> bool:
        """
        Processes a single user interaction event.

        Args:
            user_id: The interacting user.
            article_id: The article that was interacted with.
            interaction_type: click/bookmark/share/dwell/not_interested/
                              hide_story/mute_category/mute_publisher
            dwell_seconds: Seconds spent on the article (for dwell interactions).
            category: Category name — required for mute_category interactions.
            publisher_id: Publisher ID — required for mute_publisher interactions.

        Returns:
            True on success, False on failure.
        """
        # Step 1: Resolve article_id → story_id
        stmt = select(Article).where(Article.id == article_id)
        res = await self.db.execute(stmt)
        article = res.scalar_one_or_none()

        if article is None:
            logger.warning(f"Article {article_id} not found — skipping interaction")
            return False

        story_id = article.story_id
        if story_id is None:
            logger.warning(f"Article {article_id} has no associated story — skipping")
            return False

        # Step 2: Handle mute interactions
        if settings.ENABLE_NEGATIVE_FEEDBACK:
            if interaction_type == "mute_category" and category:
                await self.preference_engine.add_mute(user_id, "category", category)
                logger.info(f"User {user_id} muted category: {category}")

            elif interaction_type == "mute_publisher" and publisher_id:
                await self.preference_engine.add_mute(user_id, "publisher", publisher_id)
                logger.info(f"User {user_id} muted publisher: {publisher_id}")

        # Step 3: Update preference vector via EMA
        success = await self.preference_engine.update_preference_vector(
            user_id=user_id,
            story_id=story_id,
            interaction_type=interaction_type,
            dwell_seconds=dwell_seconds,
        )

        # Step 4: Persist interaction record
        interaction = UserInteraction(
            user_id=user_id,
            article_id=article_id,
            interaction_type=interaction_type,
            dwell_seconds=dwell_seconds,
        )
        self.db.add(interaction)
        await self.db.commit()

        logger.debug(
            f"Interaction processed: user={user_id}, article={article_id}, "
            f"type={interaction_type}, success={success}"
        )
        return success
