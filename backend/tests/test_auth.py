import pytest
import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.database.models.user import User
from app.utils.auth import hash_password, verify_password, decode_access_token
from app.main import app
from app.database.connection import get_db


@pytest_asyncio.fixture
async def client():
    async with AsyncClient(app=app, base_url="http://test") as ac:
        yield ac


@pytest_asyncio.fixture(autouse=True)
async def override_db(db_session: AsyncSession):
    """Override get_db dependency in FastAPI app with function-scoped SQLite db_session."""
    async def _get_db_override():
        yield db_session

    app.dependency_overrides[get_db] = _get_db_override
    yield
    app.dependency_overrides.pop(get_db, None)


@pytest.mark.asyncio
async def test_password_hashing_utilities():
    """Verify password hashing and verification math works cleanly."""
    pwd = "MySuperSecret123"
    hashed = hash_password(pwd)
    
    assert hashed != pwd
    assert verify_password(pwd, hashed) is True
    assert verify_password("WrongPassword", hashed) is False


@pytest.mark.asyncio
async def test_signup_endpoint(client: AsyncClient, db_session: AsyncSession):
    """Verify signup endpoint registers users and sets onboarding properties."""
    email = "new_user@test.com"
    pwd = "securepassword123"
    
    response = await client.post(
        "/api/v1/auth/signup",
        json={"email": email, "password": pwd}
    )
    
    assert response.status_code == 201
    res_json = response.json()
    assert res_json["email"] == email
    assert "id" in res_json
    assert res_json["onboarding_complete"] is False
    
    # Assert database records
    stmt = select(User).where(User.email == email)
    result = await db_session.execute(stmt)
    user = result.scalar_one_or_none()
    assert user is not None
    assert verify_password(pwd, user.hashed_password) is True


@pytest.mark.asyncio
async def test_signup_duplicate_raises_409(client: AsyncClient):
    """Verify signup with an already registered email throws a 409 Conflict."""
    email = "dup@test.com"
    
    # Initial signup
    await client.post(
        "/api/v1/auth/signup",
        json={"email": email, "password": "password123"}
    )
    
    # Duplicate signup
    response = await client.post(
        "/api/v1/auth/signup",
        json={"email": email, "password": "password123"}
    )
    
    assert response.status_code == 409
    assert "already registered" in response.json()["detail"].lower()


@pytest.mark.asyncio
async def test_login_success(client: AsyncClient):
    """Verify login verifies credentials and returns a valid signed JWT."""
    email = "login_test@test.com"
    pwd = "correctpassword"
    
    # Sign up
    await client.post(
        "/api/v1/auth/signup",
        json={"email": email, "password": pwd}
    )
    
    # Login
    response = await client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": pwd}
    )
    
    assert response.status_code == 200
    res_json = response.json()
    assert "access_token" in res_json
    assert res_json["token_type"] == "bearer"
    
    # Verify token payload
    token = res_json["access_token"]
    payload = decode_access_token(token)
    assert payload is not None
    assert payload["sub"] == email


@pytest.mark.asyncio
async def test_login_invalid_credentials(client: AsyncClient):
    """Verify login with incorrect email or password returns 401 Unauthorized."""
    email = "invalid@test.com"
    
    # Login direct
    response = await client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": "somepassword"}
    )
    
    assert response.status_code == 401
    assert "Invalid email or password" in response.json()["detail"]


@pytest.mark.asyncio
async def test_get_me_endpoint_requires_auth(client: AsyncClient):
    """Verify get_me endpoint rejects unauthenticated requests with 401."""
    response = await client.get("/api/v1/auth/me")
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_get_me_success(client: AsyncClient):
    """Verify get_me endpoint resolves successfully when auth header is provided."""
    email = "me_user@test.com"
    pwd = "password123"
    
    # Sign up
    await client.post(
        "/api/v1/auth/signup",
        json={"email": email, "password": pwd}
    )
    
    # Login to get token
    login_res = await client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": pwd}
    )
    token = login_res.json()["access_token"]
    
    headers = {"Authorization": f"Bearer {token}"}
    response = await client.get("/api/v1/auth/me", headers=headers)
    
    assert response.status_code == 200
    assert response.json()["email"] == email


@pytest.mark.asyncio
async def test_onboarding_success(client: AsyncClient):
    email = "onboard_user@test.com"
    pwd = "password123"
    
    await client.post(
        "/api/v1/auth/signup",
        json={"email": email, "password": pwd}
    )
    
    login_res = await client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": pwd}
    )
    token = login_res.json()["access_token"]
    
    headers = {"Authorization": f"Bearer {token}"}
    onboard_payload = {
        "name": "Heimdall User",
        "country": "India",
        "preferred_categories": ["Technology", "Science"],
        "preferred_publishers": ["bbc"],
        "theme": "dark",
        "brief_time": "morning"
    }
    
    response = await client.post("/api/v1/auth/onboard", json=onboard_payload, headers=headers)
    assert response.status_code == 200
    res_json = response.json()
    assert res_json["onboarding_complete"] is True
    assert res_json["name"] == "Heimdall User"
    assert res_json["country"] == "India"
    assert "Technology" in res_json["preferred_categories"]


@pytest.mark.asyncio
async def test_delete_account_success(client: AsyncClient, db_session: AsyncSession):
    email = "delete_user@test.com"
    pwd = "password123"
    
    await client.post(
        "/api/v1/auth/signup",
        json={"email": email, "password": pwd}
    )
    
    login_res = await client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": pwd}
    )
    token = login_res.json()["access_token"]
    
    headers = {"Authorization": f"Bearer {token}"}
    response = await client.delete("/api/v1/auth/account", headers=headers)
    assert response.status_code == 204
    
    # Assert database user is gone
    stmt = select(User).where(User.email == email)
    result = await db_session.execute(stmt)
    assert result.scalar_one_or_none() is None
