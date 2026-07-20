import pytest
import pytest_asyncio
import uuid
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime, timezone

from app.database.models.story import Story
from app.database.models.article import Article
from app.database.models.publisher import Publisher
from app.main import app
from app.database.connection import get_db


@pytest_asyncio.fixture
async def client():
    async with AsyncClient(app=app, base_url="http://test") as ac:
        yield ac


@pytest_asyncio.fixture(autouse=True)
async def override_db(db_session: AsyncSession):
    async def _get_db_override():
        yield db_session
    app.dependency_overrides[get_db] = _get_db_override
    yield
    app.dependency_overrides.pop(get_db, None)


@pytest.mark.asyncio
async def test_search_stories_empty_query(client: AsyncClient):
    response = await client.get("/api/v1/search?q=")
    assert response.status_code == 400


@pytest.mark.asyncio
async def test_search_stories_success(client: AsyncClient, db_session: AsyncSession):
    pub = Publisher(
        id="reuters",
        name="Reuters",
        base_url="reuters.com",
        rss_url="reuters.com/rss",
        credibility_score=0.95
    )
    db_session.add(pub)

    story = Story(
        id=uuid.uuid4(),
        title="Breaking Tech News on Quantum Computing",
        summary="A summary of computing updates.",
        status="ACTIVE",
        predicted_category="Technology",
        first_reported_at=datetime.now(timezone.utc),
        last_updated_at=datetime.now(timezone.utc),
        publisher_diversity=1,
        article_count=1,
        region_tags=["US"]
    )
    db_session.add(story)
    await db_session.flush()

    art = Article(
        id=uuid.uuid4(),
        story_id=story.id,
        publisher_id=pub.id,
        title="Quantum Computing Article",
        body_text="Body text of computing.",
        canonical_url="https://reuters.com/quantum",
        source_url="https://reuters.com/quantum",
        published_at=datetime.now(timezone.utc),
        content_hash="mock_content_hash_1",
        article_hash="mock_article_hash_1"
    )
    db_session.add(art)
    await db_session.commit()

    # Search for "Quantum" (should find the story via title/summary LIKE fallback)
    response = await client.get("/api/v1/search?q=Quantum")
    assert response.status_code == 200
    res_json = response.json()
    assert len(res_json["results"]) == 1
    assert res_json["results"][0]["title"] == "Breaking Tech News on Quantum Computing"

    # Search with category filter
    response_cat = await client.get("/api/v1/search?q=Quantum&category=Technology")
    assert len(response_cat.json()["results"]) == 1

    # Search with mismatched category
    response_cat_miss = await client.get("/api/v1/search?q=Quantum&category=Sports")
    assert len(response_cat_miss.json()["results"]) == 0
