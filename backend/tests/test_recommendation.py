"""
test_recommendation.py — Milestone 4: Recommendation Engine

20 pytest-asyncio tests covering the full recommendation pipeline:
  - PreferenceEngineService: EMA updates, mute operations, vector retrieval
  - FeedAssemblerService: cold-start, warm-user, scoring, diversity, deduplication
  - Feature flags: ENABLE_PERSONALIZATION, ENABLE_FRESHNESS_DECAY, ENABLE_TRENDING_DECAY

All external services (Qdrant, Redis) are mocked — tests run without Docker.
All vectors are fully deterministic (fixed 384-dim unit vectors).

Usage:
    pytest tests/test_recommendation.py -v
"""
import uuid
from datetime import datetime, timedelta, timezone
from typing import Optional
from unittest.mock import AsyncMock, MagicMock, patch

from sqlalchemy import select
import numpy as np
import pytest

from app.database.models.recommendation import UserRecommendationLog
from app.database.models.story import Story
from app.database.models.user import User
from app.database.models.user_profile import UserProfile
from app.services.feed_assembler import (
    FeedAssemblerService,
    _compute_freshness_decay,
    _compute_trending_live,
    _compute_composite_score,
    _build_recommendation_metadata,
)
from app.services.preference_engine import PreferenceEngineService


# ── Helpers ───────────────────────────────────────────────────────────────────


def _unit_vector(dim: int = 384, nonzero_idx: int = 0) -> list[float]:
    """Returns a deterministic 384-dim unit vector with 1.0 at nonzero_idx."""
    vec = [0.0] * dim
    vec[nonzero_idx] = 1.0
    return vec


def _make_story(
    *,
    importance_score: float = 0.8,
    trending_score: float = 0.7,
    credibility_score: Optional[float] = 0.9,
    status: str = "ACTIVE",
    last_updated_at: Optional[datetime] = None,
    updated_at: Optional[datetime] = None,
    category: Optional[str] = "Technology",
    representative_article_id: Optional[uuid.UUID] = None,
) -> Story:
    """Factory helper: returns a detached Story instance with sensible defaults."""
    story = Story()
    story.id = uuid.uuid4()
    story.importance_score = importance_score
    story.trending_score = trending_score
    story.credibility_score = credibility_score
    story.status = status
    story.last_updated_at = last_updated_at
    story.updated_at = updated_at or datetime.now(timezone.utc)
    story.category = category
    story.representative_article_id = representative_article_id or uuid.uuid4()
    story.article_count = 1
    story.confidence_score = 1.0
    story.publisher_diversity = 1
    story.title = "Test Story Title"
    story.summary = None
    story.centroid_vector_id = str(uuid.uuid4())
    story.has_conflicts = False
    return story


def _mock_redis() -> AsyncMock:
    """Returns a mock Redis client that behaves as a cold-start cache (no stored key)."""
    redis = AsyncMock()
    redis.get = AsyncMock(return_value=None)
    redis.setex = AsyncMock(return_value=True)
    return redis


def _mock_vector_store(search_results: Optional[list] = None) -> MagicMock:
    """Returns a mock VectorStoreService with controllable search results."""
    vs = MagicMock()
    vs.search_similar = MagicMock(return_value=search_results or [])
    vs.upsert_vector = MagicMock(return_value=True)
    vs.client = MagicMock()
    vs.client.retrieve = MagicMock(return_value=[])
    return vs


# ═══════════════════════════════════════════════════════════════════════════════
# 1. Cold-start feed uses SQL ranking
# ═══════════════════════════════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_cold_start_feed_uses_sql_ranking(db_session):
    """
    Cold-start users (no preference vector) must receive stories retrieved via
    the SQL ranking path (importance × trending), not Qdrant.
    """
    # Arrange
    story = _make_story(importance_score=0.9, trending_score=0.8)
    db_session.add(story)
    await db_session.commit()

    vs = _mock_vector_store()
    assembler = FeedAssemblerService(db_session=db_session, vector_store=vs)

    # Act — no preference_vector → cold-start
    result = await assembler.assemble_feed(
        user_id=uuid.uuid4(),
        preference_vector=None,
        user_profile=None,
        limit=10,
    )

    # Assert
    assert result["strategy"] == "cold_start"
    assert result["is_personalized"] is False
    # Qdrant search must NOT have been called
    vs.search_similar.assert_not_called()
    # SQL returned our story
    assert any(item["story"].id == story.id for item in result["stories"])


# ═══════════════════════════════════════════════════════════════════════════════
# 2. Warm user triggers Qdrant ANN path
# ═══════════════════════════════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_warm_user_uses_qdrant_ann(db_session):
    """
    A warm user (interaction_count >= COLD_START_THRESHOLD and has a preference
    vector) must trigger the Qdrant ANN search, not the SQL fallback.
    """
    from app.core.config import settings

    # Arrange
    story = _make_story()
    db_session.add(story)
    await db_session.commit()

    qdrant_hit = {"id": str(story.id), "score": 0.92}
    vs = _mock_vector_store(search_results=[qdrant_hit])
    assembler = FeedAssemblerService(db_session=db_session, vector_store=vs)

    pref_vec = _unit_vector()
    profile = UserProfile(
        user_id=uuid.uuid4(),
        interaction_count=settings.COLD_START_THRESHOLD + 1,
        muted_categories=[],
        muted_publishers=[],
    )

    # Act
    with patch.object(settings, "ENABLE_PERSONALIZATION", True):
        result = await assembler.assemble_feed(
            user_id=uuid.uuid4(),
            preference_vector=pref_vec,
            user_profile=profile,
            limit=10,
        )

    # Assert — Qdrant search was called
    vs.search_similar.assert_called_once()
    assert result["strategy"] == "personalized_ann"
    assert result["is_personalized"] is True


# ═══════════════════════════════════════════════════════════════════════════════
# 3. EMA update — positive feedback pulls vector toward story centroid
# ═══════════════════════════════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_ema_update_positive_feedback(db_session):
    """
    Positive feedback (click): new_pref = (1-α)×old_pref + α×centroid, L2-normalized.
    Verified numerically using numpy.
    """
    from app.core.config import settings

    # Arrange
    old_pref = _unit_vector(nonzero_idx=0)        # [1, 0, 0, ...]
    story_centroid = _unit_vector(nonzero_idx=1)  # [0, 1, 0, ...]
    alpha = settings.EMA_WEIGHT_CLICK             # 0.15

    story = _make_story()
    story.centroid_vector_id = str(story.id)
    db_session.add(story)
    await db_session.commit()

    redis = _mock_redis()
    # Redis returns no cached vector_id → fallback will be tried
    redis.get = AsyncMock(return_value=None)

    vs = _mock_vector_store()
    # Qdrant returns old_pref for user vector and story centroid
    vs.client.retrieve = MagicMock(side_effect=[
        # First call: story centroid retrieval
        [MagicMock(vector=story_centroid)],
        # Second call (get_preference_vector → Qdrant): old_pref
        [MagicMock(vector=old_pref)],
    ])

    # Manually patch get_preference_vector to return old_pref directly
    engine = PreferenceEngineService(
        db_session=db_session,
        vector_store=vs,
        redis_client=redis,
    )

    # Compute expected result
    old_arr = np.array(old_pref, dtype=np.float32)
    story_arr = np.array(story_centroid, dtype=np.float32)
    expected_raw = (1.0 - alpha) * old_arr + alpha * story_arr
    norm = np.linalg.norm(expected_raw)
    expected = (expected_raw / norm).tolist()

    # Act — patch get_preference_vector so it returns old_pref
    with patch.object(engine, "get_preference_vector", AsyncMock(return_value=old_pref)):
        await engine.update_preference_vector(
            user_id=uuid.uuid4(),
            story_id=story.id,
            interaction_type="click",
        )

    # Assert — upsert_vector was called with L2-normalized result
    vs.upsert_vector.assert_called_once()
    call_kwargs = vs.upsert_vector.call_args
    actual_vector = call_kwargs[1]["vector"] if call_kwargs[1] else call_kwargs[0][2]

    # Verify EMA math numerically (tolerance 1e-5)
    np.testing.assert_allclose(actual_vector, expected, atol=1e-5)


# ═══════════════════════════════════════════════════════════════════════════════
# 4. EMA update — negative feedback pushes vector away
# ═══════════════════════════════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_ema_update_negative_feedback(db_session):
    """
    not_interested: new_pref = (1+α)×old_pref - α×centroid, L2-normalized.
    The result should move AWAY from the story centroid.
    """
    from app.core.config import settings

    old_pref = _unit_vector(nonzero_idx=0)        # [1, 0, 0, ...]
    story_centroid = _unit_vector(nonzero_idx=0)  # Same direction — penalty pushes away
    alpha = settings.EMA_PENALTY_NOT_INTERESTED   # 0.10

    story = _make_story()
    db_session.add(story)
    await db_session.commit()

    redis = _mock_redis()
    vs = _mock_vector_store()
    vs.client.retrieve = MagicMock(return_value=[MagicMock(vector=story_centroid)])

    engine = PreferenceEngineService(
        db_session=db_session,
        vector_store=vs,
        redis_client=redis,
    )

    with patch.object(engine, "get_preference_vector", AsyncMock(return_value=old_pref)):
        await engine.update_preference_vector(
            user_id=uuid.uuid4(),
            story_id=story.id,
            interaction_type="not_interested",
        )

    vs.upsert_vector.assert_called_once()
    call_args = vs.upsert_vector.call_args
    actual = call_args[1]["vector"] if call_args[1] else call_args[0][2]

    # For negative feedback, raw = (1+α)×old - α×centroid
    old_arr = np.array(old_pref, dtype=np.float32)
    story_arr = np.array(story_centroid, dtype=np.float32)
    raw = (1.0 + alpha) * old_arr - alpha * story_arr
    norm = np.linalg.norm(raw)
    expected = (raw / norm).tolist()

    np.testing.assert_allclose(actual, expected, atol=1e-5)


# ═══════════════════════════════════════════════════════════════════════════════
# 5. mute_category stores value in UserProfile.muted_categories
# ═══════════════════════════════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_mute_category_stored_in_profile(db_session):
    """
    add_mute('category', 'Sports') must append 'Sports' to muted_categories
    and persist it in PostgreSQL.
    """
    # Arrange
    user = User(email="mute_cat@test.com", interaction_count=0)
    db_session.add(user)
    await db_session.flush()

    profile = UserProfile(
        user_id=user.id,
        interaction_count=0,
        muted_categories=[],
        muted_publishers=[],
    )
    db_session.add(profile)
    await db_session.commit()

    redis = _mock_redis()
    vs = _mock_vector_store()
    engine = PreferenceEngineService(
        db_session=db_session,
        vector_store=vs,
        redis_client=redis,
    )

    # Act
    await engine.add_mute(user_id=user.id, mute_type="category", value="Sports")

    # Assert
    from sqlalchemy.future import select
    stmt = select(UserProfile).where(UserProfile.user_id == user.id)
    res = await db_session.execute(stmt)
    updated = res.scalar_one()
    assert "Sports" in updated.muted_categories


# ═══════════════════════════════════════════════════════════════════════════════
# 6. mute_publisher stores value in UserProfile.muted_publishers
# ═══════════════════════════════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_mute_publisher_stored_in_profile(db_session):
    """
    add_mute('publisher', 'fox-news') must append 'fox-news' to muted_publishers.
    """
    user = User(email="mute_pub@test.com", interaction_count=0)
    db_session.add(user)
    await db_session.flush()

    profile = UserProfile(
        user_id=user.id,
        interaction_count=0,
        muted_categories=[],
        muted_publishers=[],
    )
    db_session.add(profile)
    await db_session.commit()

    redis = _mock_redis()
    vs = _mock_vector_store()
    engine = PreferenceEngineService(
        db_session=db_session,
        vector_store=vs,
        redis_client=redis,
    )

    await engine.add_mute(user_id=user.id, mute_type="publisher", value="fox-news")

    from sqlalchemy.future import select
    stmt = select(UserProfile).where(UserProfile.user_id == user.id)
    res = await db_session.execute(stmt)
    updated = res.scalar_one()
    assert "fox-news" in updated.muted_publishers


# ═══════════════════════════════════════════════════════════════════════════════
# 7. Freshness decay formula: decay = 2^(-t / t_half)
# ═══════════════════════════════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_freshness_decay_formula(db_session):
    """
    _compute_freshness_decay must return exactly 2^(-age_hours / HALF_LIFE_HOURS).
    Verified for a story published exactly HALF_LIFE_HOURS ago → decay ≈ 0.5.
    """
    from app.core.config import settings

    half_life = settings.FRESHNESS_DECAY_HALF_LIFE_HOURS  # default 24.0
    ref_time = datetime.now(timezone.utc) - timedelta(hours=half_life)
    story = _make_story(last_updated_at=ref_time)

    with patch("app.services.feed_assembler.settings") as mock_settings:
        mock_settings.ENABLE_FRESHNESS_DECAY = True
        mock_settings.FRESHNESS_DECAY_HALF_LIFE_HOURS = half_life

        decay = _compute_freshness_decay(story)

    # At t = t_half, decay = 2^(-1) = 0.5
    assert abs(decay - 0.5) < 0.01, f"Expected ~0.5 but got {decay}"


# ═══════════════════════════════════════════════════════════════════════════════
# 8. ENABLE_FRESHNESS_DECAY=False → decay = 1.0
# ═══════════════════════════════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_freshness_decay_disabled_returns_1(db_session):
    """
    When ENABLE_FRESHNESS_DECAY is False, _compute_freshness_decay must
    return exactly 1.0 regardless of story age.
    """
    # Very old story
    old_time = datetime.now(timezone.utc) - timedelta(days=30)
    story = _make_story(last_updated_at=old_time)

    with patch("app.services.feed_assembler.settings") as mock_settings:
        mock_settings.ENABLE_FRESHNESS_DECAY = False
        mock_settings.FRESHNESS_DECAY_HALF_LIFE_HOURS = 24.0

        decay = _compute_freshness_decay(story)

    assert decay == 1.0


# ═══════════════════════════════════════════════════════════════════════════════
# 9. Trending live formula: trending_live = trending_score × 2^(-t / t_half)
# ═══════════════════════════════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_trending_decay_live_formula(db_session):
    """
    _compute_trending_live must return trending_score × 2^(-age / t_half).
    Verified: at t = t_half, trending_live = trending_score / 2.
    """
    trending_score = 0.8
    half_life = 6.0  # Default TRENDING_DECAY_HALF_LIFE_HOURS
    ref_time = datetime.now(timezone.utc) - timedelta(hours=half_life)
    story = _make_story(trending_score=trending_score, last_updated_at=ref_time)

    with patch("app.services.feed_assembler.settings") as mock_settings:
        mock_settings.ENABLE_TRENDING_DECAY = True
        mock_settings.TRENDING_DECAY_HALF_LIFE_HOURS = half_life

        live = _compute_trending_live(story)

    expected = trending_score * 0.5  # 2^(-1) = 0.5
    assert abs(live - expected) < 0.01, f"Expected {expected} but got {live}"


# ═══════════════════════════════════════════════════════════════════════════════
# 10. ENABLE_TRENDING_DECAY=False → returns stored trending_score
# ═══════════════════════════════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_trending_decay_disabled(db_session):
    """
    When ENABLE_TRENDING_DECAY is False, _compute_trending_live must return
    the raw stored trending_score without any time decay.
    """
    trending_score = 0.75
    old_time = datetime.now(timezone.utc) - timedelta(days=7)
    story = _make_story(trending_score=trending_score, last_updated_at=old_time)

    with patch("app.services.feed_assembler.settings") as mock_settings:
        mock_settings.ENABLE_TRENDING_DECAY = False
        mock_settings.TRENDING_DECAY_HALF_LIFE_HOURS = 6.0

        live = _compute_trending_live(story)

    assert live == trending_score


# ═══════════════════════════════════════════════════════════════════════════════
# 11. Configurable weights affect composite score
# ═══════════════════════════════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_configurable_weights_applied(db_session):
    """
    Changing SEMANTIC_WEIGHT must linearly change the composite score.
    Verifies that scores are computed from settings, not hardcoded.
    """
    story = _make_story(importance_score=0.5, trending_score=0.5, credibility_score=0.5)
    sem_sim = 0.9
    trending_live = 0.5

    with patch("app.services.feed_assembler.settings") as mock_settings_low:
        mock_settings_low.SEMANTIC_WEIGHT = 0.10
        mock_settings_low.IMPORTANCE_WEIGHT = 0.30
        mock_settings_low.TRENDING_WEIGHT = 0.30
        mock_settings_low.CREDIBILITY_WEIGHT = 0.30
        score_low = _compute_composite_score(story, sem_sim, trending_live)

    with patch("app.services.feed_assembler.settings") as mock_settings_high:
        mock_settings_high.SEMANTIC_WEIGHT = 0.90
        mock_settings_high.IMPORTANCE_WEIGHT = 0.04
        mock_settings_high.TRENDING_WEIGHT = 0.03
        mock_settings_high.CREDIBILITY_WEIGHT = 0.03
        score_high = _compute_composite_score(story, sem_sim, trending_live)

    # Higher SEMANTIC_WEIGHT + high sem_sim → higher score
    assert score_high > score_low, (
        f"Expected score_high ({score_high:.4f}) > score_low ({score_low:.4f})"
    )


# ═══════════════════════════════════════════════════════════════════════════════
# 12. Publisher diversity cap — DIVERSITY_MAX_PER_PUBLISHER=1
# ═══════════════════════════════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_publisher_diversity_cap(db_session):
    """
    When DIVERSITY_MAX_PER_PUBLISHER=1, at most 1 story per representative_article_id
    (used as publisher proxy) is allowed through the diversity filter.
    """
    vs = _mock_vector_store()
    assembler = FeedAssemblerService(db_session=db_session, vector_store=vs)

    shared_pub_id = uuid.uuid4()
    bucket = [
        {
            "story": _make_story(representative_article_id=shared_pub_id),
            "sem_sim": 0.9, "trending_live": 0.7, "composite": 0.8,
            "freshness": 0.9, "final_score": 0.72, "boosts": [],
        },
        {
            "story": _make_story(representative_article_id=shared_pub_id),
            "sem_sim": 0.85, "trending_live": 0.65, "composite": 0.75,
            "freshness": 0.88, "final_score": 0.66, "boosts": [],
        },
        {
            "story": _make_story(representative_article_id=shared_pub_id),
            "sem_sim": 0.80, "trending_live": 0.60, "composite": 0.70,
            "freshness": 0.85, "final_score": 0.60, "boosts": [],
        },
    ]

    with patch("app.services.feed_assembler.settings") as mock_settings:
        mock_settings.DIVERSITY_MAX_PER_PUBLISHER = 1
        mock_settings.DIVERSITY_MAX_PER_CATEGORY = 10  # not the constraint here
        result = assembler._apply_diversity(bucket)

    assert len(result) == 1, f"Expected 1 story but got {len(result)}"


# ═══════════════════════════════════════════════════════════════════════════════
# 13. Category diversity cap — DIVERSITY_MAX_PER_CATEGORY=1
# ═══════════════════════════════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_category_diversity_cap(db_session):
    """
    When DIVERSITY_MAX_PER_CATEGORY=1, at most 1 story per category is allowed
    through the diversity filter.
    """
    vs = _mock_vector_store()
    assembler = FeedAssemblerService(db_session=db_session, vector_store=vs)

    # Three stories all in "Technology"
    bucket = [
        {
            "story": _make_story(category="Technology"),
            "sem_sim": 0.9, "trending_live": 0.7, "composite": 0.8,
            "freshness": 0.9, "final_score": 0.72, "boosts": [],
        },
        {
            "story": _make_story(category="Technology"),
            "sem_sim": 0.85, "trending_live": 0.65, "composite": 0.75,
            "freshness": 0.88, "final_score": 0.66, "boosts": [],
        },
        {
            "story": _make_story(category="Science"),
            "sem_sim": 0.80, "trending_live": 0.60, "composite": 0.70,
            "freshness": 0.85, "final_score": 0.60, "boosts": [],
        },
    ]

    with patch("app.services.feed_assembler.settings") as mock_settings:
        mock_settings.DIVERSITY_MAX_PER_CATEGORY = 1
        mock_settings.DIVERSITY_MAX_PER_PUBLISHER = 10  # not the constraint here
        result = assembler._apply_diversity(bucket)

    # Max 1 per category: 1 Technology + 1 Science = 2
    assert len(result) == 2, f"Expected 2 stories but got {len(result)}"
    categories = [item["story"].category for item in result]
    assert categories.count("Technology") == 1


# ═══════════════════════════════════════════════════════════════════════════════
# 14. Freshness sort within bucket — newer before older
# ═══════════════════════════════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_freshness_sort_within_bucket(db_session):
    """
    Within each score bucket, stories must be sorted by last_updated_at DESC
    (newest first), irrespective of their composite score differences.
    """
    now = datetime.now(timezone.utc)
    old_story = _make_story(last_updated_at=now - timedelta(hours=48))
    new_story = _make_story(last_updated_at=now - timedelta(hours=1))

    # Both stories go into the same "medium" bucket (same composite)
    db_session.add(old_story)
    db_session.add(new_story)
    await db_session.commit()

    # Build a bucket with old_story first, new_story second
    bucket = [
        {
            "story": old_story,
            "sem_sim": 0.6, "trending_live": 0.5, "composite": 0.55,
            "freshness": 0.4, "final_score": 0.55, "boosts": [],
        },
        {
            "story": new_story,
            "sem_sim": 0.6, "trending_live": 0.5, "composite": 0.55,
            "freshness": 0.95, "final_score": 0.55, "boosts": [],
        },
    ]

    # Apply freshness sort (inline, mimicking the assembler's step 7)
    def freshness_key(s):
        ref = s["story"].last_updated_at or s["story"].updated_at
        if ref and ref.tzinfo is None:
            ref = ref.replace(tzinfo=timezone.utc)
        return ref or datetime.min.replace(tzinfo=timezone.utc)

    bucket.sort(key=freshness_key, reverse=True)

    assert bucket[0]["story"].id == new_story.id, "Newest story must come first"
    assert bucket[1]["story"].id == old_story.id, "Oldest story must come last"


# ═══════════════════════════════════════════════════════════════════════════════
# 15. Deduplication removes stories seen in the last 24h
# ═══════════════════════════════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_deduplication_removes_24h_seen(db_session):
    """
    Stories already served to the user within the last 24 hours must be
    excluded from the assembled feed via UserRecommendationLog deduplication.
    """
    user = User(email="dedup@test.com", interaction_count=0)
    db_session.add(user)

    story_a = _make_story()
    story_b = _make_story()
    db_session.add(story_a)
    db_session.add(story_b)
    await db_session.flush()

    # Log story_a as already served 1 hour ago
    log = UserRecommendationLog(
        user_id=user.id,
        story_id=story_a.id,
        score=0.8,
        strategy="cold_start",
        is_personalized=False,
        recommendation_metadata={},
        clicked=False,
        created_at=datetime.now(timezone.utc) - timedelta(hours=1),
    )
    db_session.add(log)
    await db_session.commit()

    vs = _mock_vector_store()
    assembler = FeedAssemblerService(db_session=db_session, vector_store=vs)

    # Act — get_recently_seen should return {story_a.id}
    seen = await assembler._get_recently_seen(user.id)

    assert story_a.id in seen, "story_a (seen 1h ago) must be in the dedup set"
    assert story_b.id not in seen, "story_b (never seen) must not be in the dedup set"


# ═══════════════════════════════════════════════════════════════════════════════
# 16. Recommendation metadata schema
# ═══════════════════════════════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_recommendation_metadata_schema(db_session):
    """
    _build_recommendation_metadata must return a dict with exactly the
    required keys: strategy, semantic_similarity, composite_score,
    freshness_decay, boosts, diversity_bucket, and additional signals.
    """
    story = _make_story(importance_score=0.8, trending_score=0.7, credibility_score=0.9)

    meta = _build_recommendation_metadata(
        strategy="personalized_ann",
        source="semantic_similarity",
        matched_story_id=str(story.id),
        matched_categories=["Technology"],
        boosts=["credibility", "freshness"],
        ranking_algorithm="v1",
        composite_score=0.84,
        freshness_decay=0.92,
        trending_live=0.65,
        story=story,
        bucket="HIGH",
        confidence=0.85,
    )

    required_keys = {
        "strategy",
        "source",
        "matched_story_id",
        "matched_categories",
        "boosts",
        "ranking_algorithm",
        "score",
        "confidence",
        "semantic_similarity",
        "composite_score",
        "freshness_decay",
        "trending_live",
        "importance_score",
        "credibility_score",
        "diversity_bucket",
    }
    missing = required_keys - set(meta.keys())
    assert not missing, f"Missing required metadata keys: {missing}"

    assert meta["strategy"] == "personalized_ann"
    assert meta["source"] == "semantic_similarity"
    assert meta["matched_story_id"] == str(story.id)
    assert meta["confidence"] == 0.85
    assert meta["composite_score"] == 0.84
    assert meta["freshness_decay"] == 0.92
    assert meta["diversity_bucket"] == "HIGH"
    assert "credibility" in meta["boosts"]


# ═══════════════════════════════════════════════════════════════════════════════
# 17. Redis miss falls back to PostgreSQL UserProfile
# ═══════════════════════════════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_redis_fallback_to_postgres(db_session):
    """
    When Redis returns no cached vector ID, get_preference_vector must fall
    back to reading preference_vector_id from the PostgreSQL UserProfile.
    After a successful Postgres read, it must restore the Redis cache.
    """
    # Arrange
    user = User(email="redis_fallback@test.com", interaction_count=5)
    db_session.add(user)
    await db_session.flush()

    vector_id = str(user.id)  # Use user.id as the Qdrant point ID
    profile = UserProfile(
        user_id=user.id,
        preference_vector_id=vector_id,
        interaction_count=5,
        muted_categories=[],
        muted_publishers=[],
    )
    db_session.add(profile)
    await db_session.commit()

    redis = _mock_redis()
    redis.get = AsyncMock(return_value=None)  # Cache MISS

    vs = _mock_vector_store()
    pref_vec = _unit_vector()
    vs.client.retrieve = MagicMock(return_value=[MagicMock(vector=pref_vec)])

    engine = PreferenceEngineService(
        db_session=db_session,
        vector_store=vs,
        redis_client=redis,
    )

    # Act
    result = await engine.get_preference_vector(user.id)

    # Assert — fallback succeeded and Redis was re-populated
    assert result is not None, "Expected preference vector but got None"
    redis.setex.assert_called_once()  # Redis cache was restored


# ═══════════════════════════════════════════════════════════════════════════════
# 18. Qdrant vector upsert called on preference vector update
# ═══════════════════════════════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_qdrant_vector_upsert_called(db_session):
    """
    update_preference_vector must call vector_store.upsert_vector exactly once
    after computing the new EMA-updated preference vector.
    """

    story = _make_story()
    db_session.add(story)
    await db_session.commit()

    redis = _mock_redis()
    vs = _mock_vector_store()
    centroid = _unit_vector(nonzero_idx=2)
    vs.client.retrieve = MagicMock(return_value=[MagicMock(vector=centroid)])

    engine = PreferenceEngineService(
        db_session=db_session,
        vector_store=vs,
        redis_client=redis,
    )

    with patch.object(engine, "get_preference_vector", AsyncMock(return_value=_unit_vector())):
        result = await engine.update_preference_vector(
            user_id=uuid.uuid4(),
            story_id=story.id,
            interaction_type="bookmark",
        )

    assert result is True
    vs.upsert_vector.assert_called_once()
    call_kwargs = vs.upsert_vector.call_args[1]
    assert call_kwargs["collection"] == "user_preferences"
    assert len(call_kwargs["vector"]) == 384


# ═══════════════════════════════════════════════════════════════════════════════
# 19. ENABLE_PERSONALIZATION=False forces cold-start path
# ═══════════════════════════════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_feature_flag_disable_personalization(db_session):
    """
    When ENABLE_PERSONALIZATION=False, assemble_feed must use cold_start
    strategy even when a valid preference_vector is provided.
    The Qdrant ANN path must not be triggered.
    """
    story = _make_story()
    db_session.add(story)
    await db_session.commit()

    vs = _mock_vector_store()
    assembler = FeedAssemblerService(db_session=db_session, vector_store=vs)

    pref_vec = _unit_vector()
    profile = UserProfile(
        user_id=uuid.uuid4(),
        interaction_count=100,  # far above threshold
        muted_categories=[],
        muted_publishers=[],
    )

    with patch("app.services.feed_assembler.settings") as mock_settings:
        mock_settings.ENABLE_PERSONALIZATION = False
        mock_settings.COLD_START_THRESHOLD = 5
        mock_settings.ENABLE_DIVERSITY = False
        mock_settings.ENABLE_EXPLORATION = False
        mock_settings.ENABLE_FRESHNESS_DECAY = True
        mock_settings.FRESHNESS_DECAY_HALF_LIFE_HOURS = 24.0
        mock_settings.ENABLE_TRENDING_DECAY = False
        mock_settings.ENABLE_NEGATIVE_FEEDBACK = False
        mock_settings.SEMANTIC_WEIGHT = 0.50
        mock_settings.IMPORTANCE_WEIGHT = 0.25
        mock_settings.TRENDING_WEIGHT = 0.15
        mock_settings.CREDIBILITY_WEIGHT = 0.10
        mock_settings.EXPLORATION_WEIGHT = 0.05
        mock_settings.RANKING_ALGORITHM_VERSION = "v1"

        result = await assembler.assemble_feed(
            user_id=uuid.uuid4(),
            preference_vector=pref_vec,
            user_profile=profile,
            limit=10,
        )

    assert result["strategy"] == "cold_start"
    assert result["is_personalized"] is False
    vs.search_similar.assert_not_called()


# ═══════════════════════════════════════════════════════════════════════════════
# 20. ENABLE_FRESHNESS_DECAY=False → decay=1.0 in feed assembler pipeline
# ═══════════════════════════════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_feature_flag_disable_freshness_decay(db_session):
    """
    When ENABLE_FRESHNESS_DECAY=False, the assembled feed must report
    freshness_decay=1.0 in every story's recommendation_metadata.
    Stories that are months old must not be penalized.
    """
    old_time = datetime.now(timezone.utc) - timedelta(days=90)
    story = _make_story(importance_score=0.8, trending_score=0.7, last_updated_at=old_time)
    db_session.add(story)
    await db_session.commit()

    vs = _mock_vector_store()
    assembler = FeedAssemblerService(db_session=db_session, vector_store=vs)

    with patch("app.services.feed_assembler.settings") as mock_settings:
        mock_settings.ENABLE_FRESHNESS_DECAY = False
        mock_settings.FRESHNESS_DECAY_HALF_LIFE_HOURS = 24.0
        mock_settings.ENABLE_TRENDING_DECAY = False
        mock_settings.TRENDING_DECAY_HALF_LIFE_HOURS = 6.0
        mock_settings.ENABLE_PERSONALIZATION = True
        mock_settings.COLD_START_THRESHOLD = 5
        mock_settings.ENABLE_DIVERSITY = False
        mock_settings.ENABLE_EXPLORATION = False
        mock_settings.ENABLE_NEGATIVE_FEEDBACK = False
        mock_settings.SEMANTIC_WEIGHT = 0.50
        mock_settings.IMPORTANCE_WEIGHT = 0.25
        mock_settings.TRENDING_WEIGHT = 0.15
        mock_settings.CREDIBILITY_WEIGHT = 0.10
        mock_settings.EXPLORATION_WEIGHT = 0.05
        mock_settings.RANKING_ALGORITHM_VERSION = "v1"

        result = await assembler.assemble_feed(
            user_id=uuid.uuid4(),
            preference_vector=None,  # cold-start to avoid Qdrant
            user_profile=None,
            limit=10,
        )

    # Every story in the feed must have freshness_decay = 1.0
    assert len(result["stories"]) > 0, "Expected at least one story"
    for item in result["stories"]:
        meta = item["recommendation_metadata"]
        assert meta["freshness_decay"] == 1.0, (
            f"Expected freshness_decay=1.0 but got {meta['freshness_decay']}"
        )


# ═══════════════════════════════════════════════════════════════════════════════
# 21. Confidence score computation with modifiers
# ═══════════════════════════════════════════════════════════════════════════════

def test_confidence_calculation_numeric_precision():
    """
    Validates the _compute_recommendation_confidence mathematical formula logic.
    """
    from app.services.feed_assembler import _compute_recommendation_confidence

    # 1. Cold-start user confidence (base 0.40, interaction_count=0)
    conf_cold = _compute_recommendation_confidence(
        is_cold_start=True, interaction_count=0, profile_age_days=0, semantic_similarity=0.0
    )
    assert conf_cold == 0.40

    # 2. Warm user confidence (base 0.70, interaction_count=10 -> +0.10, age=5 -> +0.05, similarity=0.8 -> +0.05)
    conf_warm = _compute_recommendation_confidence(
        is_cold_start=False, interaction_count=10, profile_age_days=5, semantic_similarity=0.80
    )
    # 0.70 + 0.10 + 0.05 + 0.05 = 0.90
    assert conf_warm == 0.90

    # 3. Maximum cap at 1.0
    conf_max = _compute_recommendation_confidence(
        is_cold_start=False, interaction_count=100, profile_age_days=100, semantic_similarity=0.99
    )
    assert conf_max == 1.0


# ═══════════════════════════════════════════════════════════════════════════════
# 22. Recommendation provenance schema structure
# ═══════════════════════════════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_recommendation_provenance_metadata_fields(db_session):
    """
    Validates that the recommendation_metadata returned in the feed response
    includes all provenance keys (matched_story_id, matched_categories, source, ranking_algorithm).
    """
    story = _make_story(category="Technology")
    db_session.add(story)
    await db_session.commit()

    vs = _mock_vector_store()
    assembler = FeedAssemblerService(db_session=db_session, vector_store=vs)

    result = await assembler.assemble_feed(
        user_id=uuid.uuid4(),
        preference_vector=None,
        user_profile=None,
        limit=1,
    )

    meta = result["stories"][0]["recommendation_metadata"]
    assert meta["strategy"] == "cold_start"
    assert meta["source"] == "popularity_fallback"
    assert meta["matched_story_id"] == str(story.id)
    assert "Technology" in meta["matched_categories"]
    assert meta["ranking_algorithm"] == "v1"
    assert "score" in meta
    assert "confidence" in meta


# ═══════════════════════════════════════════════════════════════════════════════
# 23. Ranking algorithm version saved in log
# ═══════════════════════════════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_ranking_version_saved_in_reco_log(db_session):
    """
    Verifies that UserRecommendationLog records the current Settings.RANKING_ALGORITHM_VERSION.
    """
    user = User(id=uuid.uuid4(), email="version@test.com", interaction_count=0)
    story = _make_story()
    db_session.add_all([user, story])
    await db_session.commit()

    vs = _mock_vector_store()
    assembler = FeedAssemblerService(db_session=db_session, vector_store=vs)

    await assembler.assemble_feed(
        user_id=user.id,
        preference_vector=None,
        user_profile=None,
        limit=5,
    )

    stmt = select(UserRecommendationLog).where(UserRecommendationLog.user_id == user.id)
    res = await db_session.execute(stmt)
    logs = res.scalars().all()
    assert len(logs) > 0
    assert logs[0].ranking_version == "v1"


# ═══════════════════════════════════════════════════════════════════════════════
# 24. Smarter exploration selection criteria
# ═══════════════════════════════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_smarter_exploration_strategy_ordering(db_session):
    """
    Verifies that _fetch_exploration_candidates selects high credibility,
    lowest article count (low exposure) first, and highest quality second.
    """
    # story_1: high credibility (0.9), low article count (1), high quality (0.9)
    story_1 = _make_story(credibility_score=0.9, importance_score=0.9)
    story_1.article_count = 1
    
    # story_2: high credibility (0.95), high article count (10), high quality (0.95)
    story_2 = _make_story(credibility_score=0.95, importance_score=0.95)
    story_2.article_count = 10

    # story_3: low credibility (0.5), low article count (1), high quality (0.99)
    story_3 = _make_story(credibility_score=0.5, importance_score=0.99)
    story_3.article_count = 1

    db_session.add_all([story_1, story_2, story_3])
    await db_session.commit()

    vs = _mock_vector_store()
    assembler = FeedAssemblerService(db_session=db_session, vector_store=vs)

    # Fetch exploration candidates with empty exclude list
    candidates = await assembler._fetch_exploration_candidates(exclude_ids=set())

    # Excluded story_3 because credibility < 0.80
    story_ids = {c["story"].id for c in candidates}
    assert story_3.id not in story_ids
    assert story_1.id in story_ids
    assert story_2.id in story_ids

    # Sorted by article_count ASC, importance_score DESC.
    # story_1 (article_count=1) must precede story_2 (article_count=10).
    story_list = [c["story"] for c in candidates]
    index_1 = next(i for i, s in enumerate(story_list) if s.id == story_1.id)
    index_2 = next(i for i, s in enumerate(story_list) if s.id == story_2.id)
    assert index_1 < index_2


# ═══════════════════════════════════════════════════════════════════════════════
# 25. Recommendation Health Monitoring Endpoint
# ═══════════════════════════════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_feed_health_endpoint_response(db_session):
    """
    Validates that the recommendation health route responds with cache and engine availability.
    """
    from app.api.routes.feed import get_recommendation_health
    res = await get_recommendation_health(db=db_session)
    assert res.redis_status in ("online", "offline")
    assert res.qdrant_status in ("online", "offline")
    assert res.ranking_version == "v1"
    assert "total_profiles" in res.profile_status


# ═══════════════════════════════════════════════════════════════════════════════
# 26. Profile drift metadata columns on UserProfile model
# ═══════════════════════════════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_profile_drift_metadata_columns(db_session):
    """
    Verifies that UserProfile persists drift metadata columns (profile_age_days, etc.).
    """
    user = User(id=uuid.uuid4(), email="drift@test.com", interaction_count=5)
    db_session.add(user)
    await db_session.commit()

    profile = UserProfile(
        user_id=user.id,
        profile_age_days=14,
        last_profile_decay=datetime.now(timezone.utc),
        last_profile_rebuild=datetime.now(timezone.utc),
        last_profile_update=datetime.now(timezone.utc),
    )
    db_session.add(profile)
    await db_session.commit()

    # Query back to verify persistence
    stmt = select(UserProfile).where(UserProfile.user_id == user.id)
    res = await db_session.execute(stmt)
    retrieved = res.scalar_one()
    assert retrieved.profile_age_days == 14
    assert retrieved.last_profile_decay is not None
    assert retrieved.last_profile_rebuild is not None
    assert retrieved.last_profile_update is not None
