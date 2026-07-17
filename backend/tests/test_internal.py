import pytest
import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.config import settings
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
async def test_webhook_ingest_requires_secret(client: AsyncClient):
    # Call without secret header
    res1 = await client.post("/api/v1/internal/ingest")
    assert res1.status_code == 403

    # Call with incorrect secret
    res2 = await client.post("/api/v1/internal/ingest", headers={"X-Ingest-Secret": "wrong_token"})
    assert res2.status_code == 403

    # Call with correct secret
    res3 = await client.post("/api/v1/internal/ingest", headers={"X-Ingest-Secret": settings.INGEST_SECRET})
    # Any status code other than 403 shows signature verification passed!
    assert res3.status_code in [200, 202, 500]
