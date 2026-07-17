import pytest
import pytest_asyncio
import uuid
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime, timezone

from app.database.models.user import User
from app.database.models.story import Story
from app.database.models.bookmark import Bookmark
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
async def test_bookmark_lifecycle(client: AsyncClient, db_session: AsyncSession):
    # Setup user
    email = "bookmark@test.com"
    pwd = "password123"
    await client.post("/api/v1/auth/signup", json={"email": email, "password": pwd})
    login_res = await client.post("/api/v1/auth/login", json={"email": email, "password": pwd})
    token = login_res.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Setup story
    story = Story(
        id=uuid.uuid4(),
        title="Saved Event",
        summary="Brief summary",
        status="ACTIVE",
        predicted_category="Technology",
        first_reported_at=datetime.now(timezone.utc),
        last_updated_at=datetime.now(timezone.utc),
        publisher_diversity=1,
        article_count=1
    )
    db_session.add(story)
    await db_session.commit()

    # List bookmarks (should be empty)
    list_res = await client.get("/api/v1/bookmarks", headers=headers)
    assert list_res.status_code == 200
    assert len(list_res.json()) == 0

    # Add bookmark
    add_res = await client.post(f"/api/v1/bookmarks/{story.id}", headers=headers)
    assert add_res.status_code == 201

    # List bookmarks (should have 1 item)
    list_res2 = await client.get("/api/v1/bookmarks", headers=headers)
    assert list_res2.status_code == 200
    assert len(list_res2.json()) == 1
    assert list_res2.json()[0]["story_id"] == str(story.id)

    # Delete bookmark
    del_res = await client.delete(f"/api/v1/bookmarks/{story.id}", headers=headers)
    assert del_res.status_code == 204

    # List bookmarks again (empty)
    list_res3 = await client.get("/api/v1/bookmarks", headers=headers)
    assert len(list_res3.json()) == 0
