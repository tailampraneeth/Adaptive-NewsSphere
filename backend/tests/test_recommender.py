import pytest
import uuid
from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models.user import User
from app.database.models.story import Story
from app.database.models.article import Article
from app.database.models.publisher import Publisher
from app.database.models.reading_history import ReadingHistory
from app.services.recommender import HeimdallRecommender


@pytest.mark.asyncio
async def test_recommender_scoring(db_session: AsyncSession):
    # Setup test user (onboarding complete)
    user = User(
        id=uuid.uuid4(),
        email="test_rec@test.com",
        name="Test User",
        country="India",
        state="Telangana",
        onboarding_complete=True,
        preferred_categories=["Technology"],
        preferred_publishers=["bbc"],
        hidden_categories=[],
        hidden_publishers=[]
    )
    db_session.add(user)

    # Setup publisher
    pub = Publisher(
        id="bbc",
        name="BBC News",
        base_url="https://bbc.com",
        rss_url="https://bbc.com/rss",
        credibility_score=0.90
    )
    db_session.add(pub)
    await db_session.flush()

    # Create stories
    story1 = Story(
        id=uuid.uuid4(),
        title="Tech Story",
        summary="A summary about Tech.",
        status="ACTIVE",
        predicted_category="Technology",
        first_reported_at=datetime.now(timezone.utc),
        last_updated_at=datetime.now(timezone.utc),
        publisher_diversity=1,
        article_count=1,
        region_tags=["India", "Telangana"],
        trending_score=0.80
    )
    db_session.add(story1)

    story2 = Story(
        id=uuid.uuid4(),
        title="Sports Story",
        summary="A summary about Sports.",
        status="ACTIVE",
        predicted_category="Sports",
        first_reported_at=datetime.now(timezone.utc),
        last_updated_at=datetime.now(timezone.utc),
        publisher_diversity=1,
        article_count=1,
        region_tags=["US"],
        trending_score=0.10
    )
    db_session.add(story2)
    await db_session.flush()

    # Attach articles
    art1 = Article(
        id=uuid.uuid4(),
        story_id=story1.id,
        publisher_id=pub.id,
        title="Tech Article",
        body_text="Technology updates...",
        canonical_url="https://bbc.com/tech",
        source_url="https://bbc.com/tech",
        published_at=datetime.now(timezone.utc),
        content_hash="mock_content_hash_1",
        article_hash="mock_article_hash_1"
    )
    db_session.add(art1)

    art2 = Article(
        id=uuid.uuid4(),
        story_id=story2.id,
        publisher_id=pub.id,
        title="Sports Article",
        body_text="Sports updates...",
        canonical_url="https://bbc.com/sports",
        source_url="https://bbc.com/sports",
        published_at=datetime.now(timezone.utc),
        content_hash="mock_content_hash_2",
        article_hash="mock_article_hash_2"
    )
    db_session.add(art2)

    # Add mock reading history to satisfy cold start (> 3 reads)
    # Using 4 different stories to satisfy uq_user_story_reading_history
    for i in range(4):
        temp_story = Story(
            id=uuid.uuid4(),
            title=f"Temp Story {i}",
            summary="Summary",
            status="ACTIVE",
            predicted_category="Sports",
            first_reported_at=datetime.now(timezone.utc),
            last_updated_at=datetime.now(timezone.utc),
            publisher_diversity=1,
            article_count=1
        )
        db_session.add(temp_story)
        rh = ReadingHistory(
            id=uuid.uuid4(),
            user_id=user.id,
            story_id=temp_story.id,
            read_pct=50,
            dwell_seconds=30,
            interaction_type="read"
        )
        db_session.add(rh)

    await db_session.commit()

    recommender = HeimdallRecommender(db_session)
    results, _ = await recommender.get_feed(user, limit=10)

    # Tech story should rank higher because Technology is preferred, it matches user's state (Telangana), and has higher trending_score
    assert len(results) >= 2
    assert results[0].story.id == story1.id
    assert results[0].score > results[1].score
    assert "you read Technology" in results[0].explanation


@pytest.mark.asyncio
async def test_recommender_completion_feedback(db_session: AsyncSession):
    # Setup test user
    user = User(
        id=uuid.uuid4(),
        email="test_feed@test.com",
        name="Feedback User",
        country="India",
        onboarding_complete=True,
        preferred_categories=["Technology"],
        preferred_publishers=[],
        hidden_categories=[],
        hidden_publishers=[]
    )
    db_session.add(user)

    pub = Publisher(
        id="bbc",
        name="BBC",
        base_url="bbc.com",
        rss_url="bbc.com/rss",
        credibility_score=0.90
    )
    db_session.add(pub)

    story = Story(
        id=uuid.uuid4(),
        title="Tech Event",
        summary="Summary...",
        status="ACTIVE",
        predicted_category="Technology",
        first_reported_at=datetime.now(timezone.utc),
        last_updated_at=datetime.now(timezone.utc),
        publisher_diversity=1,
        article_count=1
    )
    db_session.add(story)
    await db_session.flush()

    art = Article(
        id=uuid.uuid4(),
        story_id=story.id,
        publisher_id=pub.id,
        title="Tech Art",
        body_text="Body...",
        canonical_url="https://bbc.com/art",
        source_url="https://bbc.com/art",
        published_at=datetime.now(timezone.utc),
        content_hash="mock_content_hash_3",
        article_hash="mock_article_hash_3"
    )
    db_session.add(art)

    # Simulate completed reads for Technology category (avg pct >= 70%)
    # Using 4 different stories to satisfy uq_user_story_reading_history
    for i in range(4):
        temp_story = Story(
            id=uuid.uuid4(),
            title=f"Feedback Tech Story {i}",
            summary="Summary",
            status="ACTIVE",
            predicted_category="Technology",
            first_reported_at=datetime.now(timezone.utc),
            last_updated_at=datetime.now(timezone.utc),
            publisher_diversity=1,
            article_count=1
        )
        db_session.add(temp_story)
        rh = ReadingHistory(
            id=uuid.uuid4(),
            user_id=user.id,
            story_id=temp_story.id,
            read_pct=85,
            dwell_seconds=60,
            interaction_type="finish"
        )
        db_session.add(rh)

    await db_session.commit()

    recommender = HeimdallRecommender(db_session)
    results, _ = await recommender.get_feed(user, limit=10)

    # Verify score has completion boost applied
    assert len(results) > 0
    assert results[0].score > 0.50
