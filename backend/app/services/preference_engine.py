"""
PreferenceEngineService — Milestone 4: Recommendation Engine.

Manages user preference embeddings for the personalized feed pipeline.

Architecture:
  - Qdrant "user_preferences" collection is the SINGLE SOURCE OF TRUTH for vectors.
  - Redis caches the Qdrant point ID (key: "pref:{user_id}") for sub-millisecond reads.
  - PostgreSQL user_profiles stores lightweight metadata only (no raw vectors).

Preference Vector Updates:
  Each interaction updates the user's 384-dim preference vector using an
  Exponential Moving Average (EMA) against the interacted story's centroid:

      new_pref = (1 - α) × old_pref + α × story_centroid   [positive feedback]
      new_pref = (1 + α) × old_pref - α × story_centroid   [negative feedback]

  The result is L2-normalized to maintain unit-vector cosine comparability.

All weights (α values) are fully configurable via settings — no hardcoding.
"""
import logging
import math
import uuid
from datetime import datetime, timezone
from typing import Optional

import redis.asyncio as aioredis
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.core.config import settings
from app.database.models.user import User
from app.database.models.user_profile import UserProfile
from app.services.vector_store import VectorStoreService

logger = logging.getLogger("adaptive-newssphere.preference_engine")

# ── Interaction type → EMA weight mapping ────────────────────────────────────
# Positive weights: pull pref vector toward story centroid
# Negative weights: push pref vector away from story centroid
_INTERACTION_WEIGHTS: dict[str, float] = {}  # populated lazily from settings


def _get_interaction_weight(interaction_type: str, dwell_seconds: int = 0) -> float:
    """
    Returns the EMA alpha (α) for the given interaction type.
    Positive α: move toward story centroid (positive feedback).
    Negative α: move away from story centroid (negative feedback).
    """
    if interaction_type == "share":
        return settings.EMA_WEIGHT_SHARE
    if interaction_type == "bookmark":
        return settings.EMA_WEIGHT_BOOKMARK
    if interaction_type == "click":
        return settings.EMA_WEIGHT_CLICK
    if interaction_type == "dwell":
        return (
            settings.EMA_WEIGHT_DWELL_LONG
            if dwell_seconds >= 60
            else settings.EMA_WEIGHT_DWELL_SHORT
        )
    # Negative feedback — return as negative alpha
    if interaction_type == "not_interested":
        return -settings.EMA_PENALTY_NOT_INTERESTED
    if interaction_type == "hide_story":
        return -settings.EMA_PENALTY_HIDE_STORY
    if interaction_type in ("mute_category", "mute_publisher"):
        penalty = (
            settings.EMA_PENALTY_MUTE_CATEGORY
            if interaction_type == "mute_category"
            else settings.EMA_PENALTY_MUTE_PUBLISHER
        )
        return -penalty
    # Unknown interaction type — minimal positive signal
    return 0.05


def _l2_normalize(vec: list[float]) -> list[float]:
    """L2-normalizes a vector to unit length for cosine similarity comparability."""
    sq_sum = sum(x * x for x in vec)
    norm = math.sqrt(sq_sum)
    if norm < 1e-8:
        return vec
    return [x / norm for x in vec]


class PreferenceEngineService:
    """
    Manages user preference embeddings for the recommendation engine.

    Requires:
      - db_session: AsyncSession (injected per request)
      - vector_store: VectorStoreService (Qdrant wrapper)
      - redis_client: redis.asyncio.Redis (hot cache)
    """

    REDIS_KEY_PREFIX = "pref:"
    QDRANT_COLLECTION = "user_preferences"

    def __init__(
        self,
        db_session: AsyncSession,
        vector_store: VectorStoreService,
        redis_client: aioredis.Redis,
    ) -> None:
        self.db = db_session
        self.vector_store = vector_store
        self.redis = redis_client

    def _redis_key(self, user_id: uuid.UUID) -> str:
        return f"{self.REDIS_KEY_PREFIX}{user_id}"

    async def get_preference_vector(
        self, user_id: uuid.UUID
    ) -> Optional[list[float]]:
        """
        Fetches the user's 384-dim preference vector.

        Lookup order:
          1. Redis cache (returns Qdrant point ID)
          2. PostgreSQL user_profiles (metadata lookup)
          3. Qdrant (vector retrieval by point ID)
          4. Returns None if user is cold-start (no vector yet)
        """
        # Step 1: Redis cache hit
        vector_id = await self.redis.get(self._redis_key(user_id))
        if vector_id:
            vector_id = vector_id.decode() if isinstance(vector_id, bytes) else vector_id
            logger.debug(f"Redis cache hit for user {user_id}")
        else:
            # Step 2: Fallback to PostgreSQL metadata
            stmt = select(UserProfile).where(UserProfile.user_id == user_id)
            res = await self.db.execute(stmt)
            profile = res.scalar_one_or_none()
            if profile and profile.preference_vector_id:
                vector_id = profile.preference_vector_id
                # Restore Redis cache
                await self.redis.setex(
                    self._redis_key(user_id),
                    settings.PREFERENCE_CACHE_TTL_SECONDS,
                    vector_id
                )
                logger.info(f"Redis cache restored from Postgres for user {user_id}")
            else:
                logger.debug(f"Cold-start user — no preference vector for {user_id}")
                return None

        # Step 3: Fetch vector from Qdrant
        try:
            points = self.vector_store.client.retrieve(
                collection_name=self.QDRANT_COLLECTION,
                ids=[vector_id],
                with_vectors=True
            )
            if points and points[0].vector:
                return list(points[0].vector)
        except Exception as e:
            logger.error(f"Failed to retrieve preference vector from Qdrant: {e}")

        return None

    async def update_preference_vector(
        self,
        user_id: uuid.UUID,
        story_id: uuid.UUID,
        interaction_type: str,
        dwell_seconds: int = 0,
    ) -> bool:
        """
        Updates the user's preference vector using EMA against the story centroid.

        For negative feedback (not_interested / hide_story / mute_*),
        the vector is pushed away from the story centroid.

        Args:
            user_id: Target user UUID.
            story_id: Story the user interacted with.
            interaction_type: One of click/bookmark/share/dwell/not_interested/
                              hide_story/mute_category/mute_publisher.
            dwell_seconds: Relevant only for 'dwell' interactions.

        Returns:
            True on success, False on failure.
        """
        if not settings.ENABLE_PERSONALIZATION:
            return True  # no-op if personalization is disabled

        alpha = _get_interaction_weight(interaction_type, dwell_seconds)

        # Fetch story centroid vector from Qdrant
        story_vector_id = str(story_id)
        try:
            points = self.vector_store.client.retrieve(
                collection_name="stories",
                ids=[story_vector_id],
                with_vectors=True
            )
            if not points or not points[0].vector:
                logger.warning(f"No centroid vector in Qdrant for story {story_id}")
                return False
            story_centroid = list(points[0].vector)
        except Exception as e:
            logger.error(f"Failed to retrieve story centroid from Qdrant: {e}")
            return False

        # Fetch or initialize preference vector
        current_pref = await self.get_preference_vector(user_id)
        if current_pref is None:
            # First interaction — initialize to story centroid
            new_pref = story_centroid
        else:
            # EMA update (pure Python)
            abs_alpha = abs(alpha)
            new_raw = []
            if alpha >= 0:
                # Positive feedback: pull toward story
                for o, s in zip(current_pref, story_centroid):
                    new_raw.append((1.0 - abs_alpha) * o + abs_alpha * s)
            else:
                # Negative feedback: push away from story
                for o, s in zip(current_pref, story_centroid):
                    new_raw.append((1.0 + abs_alpha) * o - abs_alpha * s)
            new_pref = _l2_normalize(new_raw)

        # Upsert to Qdrant user_preferences collection
        point_id = str(user_id)
        success = self.vector_store.upsert_vector(
            collection=self.QDRANT_COLLECTION,
            point_id=point_id,
            vector=new_pref,
            payload={
                "user_id": str(user_id),
                "interaction_type": interaction_type,
                "updated_at": datetime.now(timezone.utc).isoformat(),
            }
        )
        if not success:
            return False

        # Cache vector ID in Redis
        await self.redis.setex(
            self._redis_key(user_id),
            settings.PREFERENCE_CACHE_TTL_SECONDS,
            point_id
        )

        # Update PostgreSQL metadata (no raw vector stored here)
        stmt = select(UserProfile).where(UserProfile.user_id == user_id)
        res = await self.db.execute(stmt)
        profile = res.scalar_one_or_none()
        if profile is None:
            profile = UserProfile(
                user_id=user_id,
                preference_vector_id=point_id,
                interaction_count=1,
                muted_categories=[],
                muted_publishers=[]
            )
            self.db.add(profile)
        else:
            profile.preference_vector_id = point_id
            profile.interaction_count += 1

        # Handle mute actions — record in profile
        if settings.ENABLE_NEGATIVE_FEEDBACK:
            if interaction_type == "mute_category":
                # Caller should pass category in payload — handled by worker
                pass
            elif interaction_type == "mute_publisher":
                pass

        # Update User.interaction_count + User.preference_vector_id
        user_stmt = select(User).where(User.id == user_id)
        user_res = await self.db.execute(user_stmt)
        user = user_res.scalar_one_or_none()
        if user:
            user.interaction_count += 1
            user.preference_vector_id = point_id

        await self.db.commit()
        logger.info(
            f"Preference vector updated for user {user_id} "
            f"(type={interaction_type}, α={alpha:.2f})"
        )
        return True

    async def add_mute(
        self,
        user_id: uuid.UUID,
        mute_type: str,
        value: str,
    ) -> None:
        """
        Adds a category or publisher to the user's mute list.

        Args:
            user_id: Target user.
            mute_type: 'category' or 'publisher'.
            value: Category name or publisher ID to mute.
        """
        stmt = select(UserProfile).where(UserProfile.user_id == user_id)
        res = await self.db.execute(stmt)
        profile = res.scalar_one_or_none()
        if profile is None:
            return

        if mute_type == "category":
            muted = list(profile.muted_categories or [])
            if value not in muted:
                muted.append(value)
                profile.muted_categories = muted
        elif mute_type == "publisher":
            muted = list(profile.muted_publishers or [])
            if value not in muted:
                muted.append(value)
                profile.muted_publishers = muted

        await self.db.commit()

    async def get_profile_health(self, user_id: uuid.UUID) -> dict:
        """
        Returns diagnostic health information for a user's preference profile.
        Used by the GET /api/v1/feed/{user_id}/profile/health endpoint.
        """
        stmt = select(UserProfile).where(UserProfile.user_id == user_id)
        res = await self.db.execute(stmt)
        profile = res.scalar_one_or_none()

        redis_cached = False
        vector_id = None
        qdrant_available = False
        vector_age_hours = None

        if profile:
            vector_id = profile.preference_vector_id
            # Check Redis
            cached = await self.redis.get(self._redis_key(user_id))
            redis_cached = cached is not None

            # Check Qdrant availability and vector age
            if vector_id:
                try:
                    points = self.vector_store.client.retrieve(
                        collection_name=self.QDRANT_COLLECTION,
                        ids=[vector_id],
                        with_vectors=False
                    )
                    qdrant_available = bool(points)
                except Exception:
                    qdrant_available = False

            if profile.last_updated_at:
                now = datetime.now(timezone.utc)
                last = profile.last_updated_at
                if last.tzinfo is None:
                    last = last.replace(tzinfo=timezone.utc)
                vector_age_hours = round((now - last).total_seconds() / 3600, 2)

        interaction_count = profile.interaction_count if profile else 0

        return {
            "user_id": str(user_id),
            "interaction_count": interaction_count,
            "is_cold_start": interaction_count < settings.COLD_START_THRESHOLD,
            "preference_vector_id": vector_id,
            "preference_vector_age_hours": vector_age_hours,
            "redis_cached": redis_cached,
            "qdrant_vector_available": qdrant_available,
            "muted_categories": list(profile.muted_categories or []) if profile else [],
            "muted_publishers": list(profile.muted_publishers or []) if profile else [],
            "last_updated_at": profile.last_updated_at.isoformat() if profile and profile.last_updated_at else None,
        }

    async def hydrate_redis_from_postgres(self) -> int:
        """
        Startup task: loads all preference_vector_ids from PostgreSQL into Redis.
        Called once during application lifespan startup.

        Returns: count of profiles hydrated.
        """
        stmt = select(UserProfile).where(UserProfile.preference_vector_id.isnot(None))
        res = await self.db.execute(stmt)
        profiles = res.scalars().all()

        count = 0
        for profile in profiles:
            if profile.preference_vector_id is not None:
                await self.redis.setex(
                    self._redis_key(profile.user_id),
                    settings.PREFERENCE_CACHE_TTL_SECONDS,
                    profile.preference_vector_id
                )
                count += 1

        logger.info(f"Redis hydrated with {count} preference vector IDs from Postgres.")
        return count
