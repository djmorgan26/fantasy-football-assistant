"""Core utilities: JWT, password hashing, encryption, config."""
from datetime import timedelta

import pytest
from httpx import AsyncClient

from app.core.auth import (
    create_access_token,
    get_password_hash,
    verify_password,
    verify_token,
)
from app.core.config import settings
from app.utils.encryption import ESPNCredentialManager, encrypt_data, decrypt_data


pytestmark = pytest.mark.unit


class TestPasswords:
    def test_hash_roundtrip(self):
        hashed = get_password_hash("s3cret-password")
        assert hashed != "s3cret-password"
        assert verify_password("s3cret-password", hashed)
        assert not verify_password("wrong", hashed)

    def test_hashes_are_salted(self):
        assert get_password_hash("same") != get_password_hash("same")


class TestTokens:
    def test_create_and_verify(self):
        token = create_access_token({"sub": "42"})
        payload = verify_token(token)
        assert payload is not None
        assert payload["sub"] == "42"
        assert "exp" in payload

    def test_expired_token_rejected(self):
        token = create_access_token({"sub": "42"}, expires_delta=timedelta(minutes=-1))
        assert verify_token(token) is None

    def test_garbage_token_rejected(self):
        assert verify_token("not-a-jwt") is None

    def test_token_signed_with_other_key_rejected(self):
        from jose import jwt

        token = jwt.encode({"sub": "42"}, "some-other-secret", algorithm="HS256")
        assert verify_token(token) is None


class TestEncryption:
    def test_roundtrip(self):
        encrypted = encrypt_data("hello world")
        assert encrypted != "hello world"
        assert decrypt_data(encrypted) == "hello world"

    def test_decrypt_garbage_returns_none(self):
        assert decrypt_data("garbage-not-encrypted") is None

    def test_espn_credential_manager_roundtrip(self):
        s2 = ESPNCredentialManager.encrypt_espn_s2("the-espn-s2-cookie")
        swid = ESPNCredentialManager.encrypt_espn_swid("{SWID-VALUE}")
        assert ESPNCredentialManager.decrypt_espn_s2(s2) == "the-espn-s2-cookie"
        assert ESPNCredentialManager.decrypt_espn_swid(swid) == "{SWID-VALUE}"


class TestConfig:
    def test_effective_database_url_in_mock_mode(self):
        original = settings.mock_mode
        try:
            settings.mock_mode = True
            assert settings.effective_database_url == settings.mock_database_url
            settings.mock_mode = False
            assert settings.effective_database_url == settings.database_url
        finally:
            settings.mock_mode = original


class TestHealthAndMeta:
    async def test_health(self, client: AsyncClient):
        resp = await client.get("/health")
        assert resp.status_code == 200
        body = resp.json()
        assert body["status"] == "healthy"
        assert "mock_mode" in body

    async def test_meta_no_demo_credentials_in_real_mode(self, client: AsyncClient):
        resp = await client.get("/api/meta")
        assert resp.status_code == 200
        assert "demo_credentials" not in resp.json()

    async def test_meta_demo_credentials_in_mock_mode(self, client: AsyncClient, mock_mode):
        resp = await client.get("/api/meta")
        assert resp.status_code == 200
        creds = resp.json()["demo_credentials"]
        assert creds["email"]
        assert creds["password"]
