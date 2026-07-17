import pytest
import pytest_asyncio
import hashlib
from datetime import datetime, timezone, timedelta
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.database.models.user import User
from app.utils.auth import hash_password, verify_password
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
async def test_forgot_password_generic_response(client: AsyncClient, db_session: AsyncSession):
    """Verify generic response is returned for both existing and non-existing emails to prevent enumeration."""
    # 1. Existing email
    email = "registered@test.com"
    pwd = "securepassword123"
    await client.post("/api/v1/auth/signup", json={"email": email, "password": pwd})
    
    response = await client.post("/api/v1/auth/forgot-password", json={"email": email})
    assert response.status_code == 200
    assert response.json() == {"message": "If the email is registered, a password reset link has been sent."}

    # 2. Non-existing email
    response_fake = await client.post("/api/v1/auth/forgot-password", json={"email": "nonexistent@test.com"})
    assert response_fake.status_code == 200
    assert response_fake.json() == {"message": "If the email is registered, a password reset link has been sent."}


@pytest.mark.asyncio
async def test_forgot_password_rate_limiting(client: AsyncClient, db_session: AsyncSession):
    """Verify password reset request rate-limiting is enforced (max once per 60s)."""
    email = "rate_limit@test.com"
    pwd = "securepassword123"
    await client.post("/api/v1/auth/signup", json={"email": email, "password": pwd})

    # First request -> Success
    response1 = await client.post("/api/v1/auth/forgot-password", json={"email": email})
    assert response1.status_code == 200

    # Second request immediately -> 429 Too Many Requests
    response2 = await client.post("/api/v1/auth/forgot-password", json={"email": email})
    assert response2.status_code == 429
    assert "Too many password reset requests" in response2.json()["detail"]


@pytest.mark.asyncio
async def test_password_reset_flow_success(client: AsyncClient, db_session: AsyncSession):
    """Verify a complete successful password reset flow."""
    email = "reset_success@test.com"
    old_pwd = "oldpassword123"
    new_pwd = "newpassword123"
    
    # 1. Sign up user
    await client.post("/api/v1/auth/signup", json={"email": email, "password": old_pwd})

    # 2. Request forgot password
    await client.post("/api/v1/auth/forgot-password", json={"email": email})

    # 3. Fetch user and token details from database
    stmt = select(User).where(User.email == email)
    result = await db_session.execute(stmt)
    user = result.scalar_one()
    assert user.reset_token_hash is not None
    assert user.reset_token_expires_at is not None

    # Since token is secure and random, we'll manually generate a mock token and hash it for testing.
    mock_token = "my-secure-password-reset-token-xyz-123"
    user.reset_token_hash = hashlib.sha256(mock_token.encode()).hexdigest()
    user.reset_token_expires_at = datetime.now(timezone.utc) + timedelta(minutes=30)
    await db_session.commit()

    # 4. Reset password
    reset_resp = await client.post(
        "/api/v1/auth/reset-password",
        json={"token": mock_token, "new_password": new_pwd}
    )
    assert reset_resp.status_code == 200
    assert reset_resp.json() == {"message": "Password reset successfully."}

    # 5. Verify database token fields are cleared (single-use)
    await db_session.refresh(user)
    assert user.reset_token_hash is None
    assert user.reset_token_expires_at is None

    # 6. Verify old password fails and new password succeeds on login
    login_old = await client.post("/api/v1/auth/login", json={"email": email, "password": old_pwd})
    assert login_old.status_code == 401

    login_new = await client.post("/api/v1/auth/login", json={"email": email, "password": new_pwd})
    assert login_new.status_code == 200
    assert "access_token" in login_new.json()


@pytest.mark.asyncio
async def test_password_reset_invalid_or_expired_token(client: AsyncClient, db_session: AsyncSession):
    """Verify that password resets fail for invalid or expired tokens."""
    email = "invalid_token@test.com"
    pwd = "password123"
    await client.post("/api/v1/auth/signup", json={"email": email, "password": pwd})
    await client.post("/api/v1/auth/forgot-password", json={"email": email})

    # Attempt with random invalid token -> 400
    reset_resp_fake = await client.post(
        "/api/v1/auth/reset-password",
        json={"token": "some-random-incorrect-token", "new_password": "newpassword123"}
    )
    assert reset_resp_fake.status_code == 400

    # Attempt with expired token -> 400
    stmt = select(User).where(User.email == email)
    result = await db_session.execute(stmt)
    user = result.scalar_one()
    
    mock_token = "expired-token-xyz"
    user.reset_token_hash = hashlib.sha256(mock_token.encode()).hexdigest()
    # set expiration to 5 minutes ago
    user.reset_token_expires_at = datetime.now(timezone.utc) - timedelta(minutes=5)
    await db_session.commit()

    reset_resp_expired = await client.post(
        "/api/v1/auth/reset-password",
        json={"token": mock_token, "new_password": "newpassword123"}
    )
    assert reset_resp_expired.status_code == 400
