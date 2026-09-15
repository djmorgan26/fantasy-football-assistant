import pytest
from httpx import AsyncClient
from app.core.auth import get_password_hash, verify_password

pytestmark = pytest.mark.integration


class TestAuth:
    def test_password_hashing(self):
        password = "testpassword123"
        hashed = get_password_hash(password)
        
        assert hashed != password
        assert verify_password(password, hashed) is True
        assert verify_password("wrongpassword", hashed) is False

    @pytest.mark.asyncio
    async def test_register_user(self, client: AsyncClient):
        response = await client.post(
            "/api/auth/register",
            json={
                "email": "test@example.com",
                "password": "testpassword123",
                "full_name": "Test User"
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"
        assert data["user"]["email"] == "test@example.com"
        assert data["user"]["full_name"] == "Test User"

    @pytest.mark.asyncio
    async def test_register_duplicate_email(self, client: AsyncClient):
        # First registration
        await client.post(
            "/api/auth/register",
            json={
                "email": "duplicate@example.com",
                "password": "testpassword123"
            }
        )
        
        # Second registration with same email
        response = await client.post(
            "/api/auth/register",
            json={
                "email": "duplicate@example.com",
                "password": "anotherpassword123"
            }
        )
        
        assert response.status_code == 400
        assert "already registered" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_login_success(self, client: AsyncClient):
        # Register user first
        await client.post(
            "/api/auth/register",
            json={
                "email": "login@example.com",
                "password": "testpassword123"
            }
        )
        
        # Login
        response = await client.post(
            "/api/auth/login",
            json={
                "email": "login@example.com",
                "password": "testpassword123"
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"
        assert data["user"]["email"] == "login@example.com"

    @pytest.mark.asyncio
    async def test_login_invalid_credentials(self, client: AsyncClient):
        response = await client.post(
            "/api/auth/login",
            json={
                "email": "nonexistent@example.com",
                "password": "wrongpassword"
            }
        )
        
        assert response.status_code == 401
        assert "Incorrect email or password" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_get_current_user(self, client: AsyncClient):
        # Register and get token
        register_response = await client.post(
            "/api/auth/register",
            json={
                "email": "currentuser@example.com",
                "password": "testpassword123",
                "full_name": "Current User"
            }
        )
        token = register_response.json()["access_token"]
        
        # Get current user
        response = await client.get(
            "/api/auth/me",
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["email"] == "currentuser@example.com"
        assert data["full_name"] == "Current User"
        assert data["is_active"] is True

    async def test_get_current_user_accepts_yahoo_proxy_session_header(self, client: AsyncClient):
        registered = await client.post(
            "/api/auth/register",
            json={"email": "yahoo-header@example.com", "password": "testpassword123"},
        )
        token = registered.json()["access_token"]

        response = await client.get(
            "/api/auth/me",
            headers={"X-Fantasy-Session": token},
        )

        assert response.status_code == 200
        assert response.json()["email"] == "yahoo-header@example.com"

    @pytest.mark.asyncio
    async def test_get_current_user_unauthorized(self, client: AsyncClient):
        response = await client.get("/api/auth/me")
        
        assert response.status_code == 401

class TestProfile:
    @pytest.mark.asyncio
    async def test_update_full_name(self, client: AsyncClient, auth_headers):
        resp = await client.put(
            "/api/auth/me",
            json={"full_name": "Renamed User"},
            headers=auth_headers,
        )
        assert resp.status_code == 200
        assert resp.json()["full_name"] == "Renamed User"

    @pytest.mark.asyncio
    async def test_change_password(self, client: AsyncClient, auth_headers):
        resp = await client.put(
            "/api/auth/me",
            json={
                "current_password": "testpassword123",
                "new_password": "newpassword456",
            },
            headers=auth_headers,
        )
        assert resp.status_code == 200

        # Old password no longer works; new one does.
        old = await client.post(
            "/api/auth/login",
            json={"email": "fixture-user@example.com", "password": "testpassword123"},
        )
        assert old.status_code == 401
        new = await client.post(
            "/api/auth/login",
            json={"email": "fixture-user@example.com", "password": "newpassword456"},
        )
        assert new.status_code == 200

    @pytest.mark.asyncio
    async def test_change_password_wrong_current(self, client: AsyncClient, auth_headers):
        resp = await client.put(
            "/api/auth/me",
            json={"current_password": "wrong", "new_password": "newpassword456"},
            headers=auth_headers,
        )
        assert resp.status_code == 400

    @pytest.mark.asyncio
    async def test_expired_token_rejected(self, client: AsyncClient):
        from datetime import timedelta
        from app.core.auth import create_access_token

        token = create_access_token({"sub": "1"}, expires_delta=timedelta(minutes=-5))
        resp = await client.get(
            "/api/auth/me", headers={"Authorization": f"Bearer {token}"}
        )
        assert resp.status_code == 401

    @pytest.mark.asyncio
    async def test_malformed_token_rejected(self, client: AsyncClient):
        resp = await client.get(
            "/api/auth/me", headers={"Authorization": "Bearer garbage"}
        )
        assert resp.status_code == 401


class TestSessionLength:
    """The token lifetime is the whole session: there is no refresh flow.

    At the old 30 minutes a user got logged out mid-use. The 401 interceptor
    clears the token and redirects to /login, so whatever they were doing is
    gone. This guards against someone trimming it back without first adding
    refresh tokens.
    """

    def test_session_outlasts_a_sitting(self):
        from app.core.config import settings

        assert settings.access_token_expire_minutes >= 60 * 12, (
            "A session shorter than half a day logs people out while they are "
            "still using the app; add a refresh flow before shortening this."
        )

    def test_token_carries_that_expiry(self):
        from datetime import datetime, timedelta, timezone

        from jose import jwt

        from app.core.auth import create_access_token
        from app.core.config import settings

        token = create_access_token(data={"sub": "1"})
        claims = jwt.decode(token, settings.secret_key, algorithms=[settings.algorithm])

        expires = datetime.fromtimestamp(claims["exp"], tz=timezone.utc)
        expected = datetime.now(timezone.utc) + timedelta(
            minutes=settings.access_token_expire_minutes
        )
        # A minute of slack for the clock between issuing and asserting.
        assert abs((expires - expected).total_seconds()) < 60
