import asyncio
import pytest
from datetime import datetime, timezone
import uuid
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.future import select
import pytest_asyncio
from app.core.config import settings
from app.database.models import (
    Base, User, Publisher, Story, Article, StoryTimeline, 
    UserInteraction, ChatSession, ChatMessage, UserRecommendationLog
)

# Test fixtures are imported automatically from conftest.py

@pytest.mark.asyncio
async def test_crud_publisher_and_article(db_session: AsyncSession):
    """Verify that publishers and articles are correctly inserted and linked."""
    # 1. Create a publisher
    publisher = Publisher(
        id="bbc",
        name="BBC News",
        base_url="https://www.bbc.com",
        credibility_score=0.95,
        bias_rating="center"
    )
    db_session.add(publisher)
    await db_session.commit()

    # Query publisher back
    result = await db_session.execute(select(Publisher).filter_by(id="bbc"))
    queried_publisher = result.scalar_one_or_none()
    assert queried_publisher is not None
    assert queried_publisher.name == "BBC News"

    # 2. Create a story
    story = Story(
        centroid_vector_id=uuid.uuid4(),
        summary_quick="Quick story highlight.",
        summary_beginner="Simple explanation of story.",
        summary_professional="Professional breakdown.",
        confidence_score=0.88
    )
    db_session.add(story)
    await db_session.commit()

    # 3. Create an article linked to publisher and story
    article = Article(
        story_id=story.id,
        publisher_id=publisher.id,
        title="Breaking Tech News",
        body_text="Here is the detailed body content of the breaking tech announcement.",
        author="Jane Doe",
        source_url="https://www.bbc.com/news/tech-12345",
        published_at=datetime.now(timezone.utc),
        content_hash="mock_content_hash_1",
        article_hash="mock_article_hash_1"
    )
    db_session.add(article)
    await db_session.commit()

    # Query article and verify relationships
    result = await db_session.execute(select(Article).filter_by(title="Breaking Tech News"))
    queried_article = result.scalar_one_or_none()
    assert queried_article is not None
    assert queried_article.publisher_id == "bbc"
    assert queried_article.story_id == story.id
    
    # Test cascade loading
    assert queried_article.publisher.name == "BBC News"
    assert queried_article.story.summary_quick == "Quick story highlight."
