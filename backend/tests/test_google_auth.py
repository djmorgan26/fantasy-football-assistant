"""Google sign-in, and especially the account-linking rules.

The tokens here are real RS256 JWTs signed by a keypair generated in-process;
the verifier's JWKS cache is primed with the matching public key. That means
every signature, audience and expiry check runs for real, rather than being
mocked past, which is the only way these tests say anything about security.
"""
import base64
import json
import time
from datetime import datetime, timedelta, timezone

import pytest
import respx
import httpx
from jose import jwt as jose_jwt
from jose.backends import RSAKey
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from sqlalchemy import select

from app.core.config import settings
from app.models.user import User
from app.services import google_oauth

KID = "test-signing-key"
CLIENT_ID = "test-client-id.apps.googleusercontent.com"

_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
PRIVATE_PEM = _key.private_bytes(
    encoding=serialization.Encoding.PEM,
    format=serialization.PrivateFormat.PKCS8,
    encryption_algorithm=serialization.NoEncryption(),
).decode()
PUBLIC_PEM = _key.public_key().public_bytes(
    encoding=serialization.Encoding.PEM,
    format=serialization.PublicFormat.SubjectPublicKeyInfo,
).decode()

_other_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
OTHER_PRIVATE_PEM = _other_key.private_bytes(
    encoding=serialization.Encoding.PEM,
    format=serialization.PrivateFormat.PKCS8,
    encryption_algorithm=serialization.NoEncryption(),
).decode()


def _jwks():
    entry = RSAKey(PUBLIC_PEM, "RS256").to_dict()
    entry["kid"] = KID
    # to_dict can hand back bytes for n/e depending on the backend; the
    # verifier passes this straight to jose, which wants str.
    return {"keys": [{k: (v.decode() if isinstance(v, bytes) else v) for k, v in entry.items()}]}


def google_token(
    sub="google-sub-12345",
    email="someone@example.com",
    email_verified=True,
    name="Someone Real",
    picture="https://lh3.googleusercontent.com/a/photo",
    aud=CLIENT_ID,
    iss="https://accounts.google.com",
    expires_in=3600,
    key=None,
    kid=KID,
    alg="RS256",
):
    now = datetime.now(tz=timezone.utc)
    claims = {
        "iss": iss,
        "aud": aud,
        "sub": sub,
        "email": email,
        "email_verified": email_verified,
        "name": name,
        "picture": picture,
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(seconds=expires_in)).timestamp()),
    }
    return jose_jwt.encode(
        claims, key or PRIVATE_PEM, algorithm=alg, headers={"kid": kid}
    )


@pytest.fixture(autouse=True)
def google_configured():
    """Point the verifier at our test keypair and audience."""
    original = settings.google_client_id
    settings.google_client_id = CLIENT_ID
    google_oauth._certs_cache = (time.monotonic(), _jwks())
    yield
    settings.google_client_id = original
    google_oauth.clear_certs_cache()


async def _register(client, email, password="testpassword123", full_name="Existing User"):
    resp = await client.post(
        "/api/auth/register",
        json={"email": email, "password": password, "full_name": full_name},
    )
    assert resp.status_code == 200, resp.text
    return resp.json()


class TestLinking:
    """The behaviour that decides whether someone keeps their leagues."""

    async def test_it_links_google_to_an_existing_password_account(self, client, db_session):
        # The real case: an account that already exists, signing in with
        # Google for the first time. It must be the SAME row, not a new one.
        registered = await _register(client, "davidjmorgan26@gmail.com")
        original_id = registered["user"]["id"]

        resp = await client.post(
            "/api/auth/google",
            json={"credential": google_token(email="davidjmorgan26@gmail.com")},
        )

        assert resp.status_code == 200, resp.text
        body = resp.json()
        assert body["outcome"] == "linked"
        assert body["user"]["id"] == original_id

        users = (await db_session.execute(select(User))).scalars().all()
        assert len(users) == 1, "linking must not create a second account"
        assert users[0].google_sub == "google-sub-12345"

    async def test_the_linked_account_keeps_its_password(self, client):
        # Linking adds a sign-in method, it does not replace one. Being able
        # to still use the password is what makes this non-destructive.
        await _register(client, "dave@example.com")
        await client.post(
            "/api/auth/google", json={"credential": google_token(email="dave@example.com")}
        )

        resp = await client.post(
            "/api/auth/login",
            json={"email": "dave@example.com", "password": "testpassword123"},
        )
        assert resp.status_code == 200, resp.text

    async def test_it_links_across_a_difference_in_email_case(self, client, db_session):
        # Registered with capitals, Google always reports lowercase. Without
        # normalization this silently creates a second account.
        await _register(client, "Dave.Morgan@Example.com")

        resp = await client.post(
            "/api/auth/google",
            json={"credential": google_token(email="dave.morgan@example.com")},
        )

        assert resp.status_code == 200, resp.text
        assert resp.json()["outcome"] == "linked"
        users = (await db_session.execute(select(User))).scalars().all()
        assert len(users) == 1

    async def test_it_creates_an_account_when_nothing_matches(self, client, db_session):
        resp = await client.post(
            "/api/auth/google", json={"credential": google_token(email="brand.new@example.com")}
        )

        assert resp.status_code == 200, resp.text
        assert resp.json()["outcome"] == "created"
        user = (await db_session.execute(select(User))).scalar_one()
        assert user.email == "brand.new@example.com"
        assert user.hashed_password is None
        assert user.full_name == "Someone Real"
        assert user.avatar_url == "https://lh3.googleusercontent.com/a/photo"

    async def test_the_second_sign_in_resumes_rather_than_relinking(self, client, db_session):
        await client.post("/api/auth/google", json={"credential": google_token()})
        resp = await client.post("/api/auth/google", json={"credential": google_token()})

        assert resp.json()["outcome"] == "signed_in"
        assert len((await db_session.execute(select(User))).scalars().all()) == 1

    async def test_it_follows_the_google_sub_when_the_google_email_changes(
        self, client, db_session
    ):
        # Google accounts can change their address. We key on `sub`, so the
        # same person arriving with a new email is still the same account and
        # does not get a second one.
        await client.post(
            "/api/auth/google", json={"credential": google_token(email="old@example.com")}
        )
        resp = await client.post(
            "/api/auth/google", json={"credential": google_token(email="new@example.com")}
        )

        assert resp.json()["outcome"] == "signed_in"
        users = (await db_session.execute(select(User))).scalars().all()
        assert len(users) == 1
        assert users[0].email == "old@example.com", "our stored address is the stable one"

    async def test_it_does_not_overwrite_a_name_the_user_set(self, client, db_session):
        await _register(client, "dave@example.com", full_name="Dave The Commissioner")
        await client.post(
            "/api/auth/google",
            json={"credential": google_token(email="dave@example.com", name="David Morgan")},
        )

        user = (await db_session.execute(select(User))).scalar_one()
        assert user.full_name == "Dave The Commissioner"


class TestLinkingRefusals:
    """An unverified email is the account-takeover vector, so it is refused."""

    async def test_an_unverified_email_cannot_claim_an_existing_account(
        self, client, db_session
    ):
        await _register(client, "davidjmorgan26@gmail.com")

        resp = await client.post(
            "/api/auth/google",
            json={
                "credential": google_token(
                    email="davidjmorgan26@gmail.com", email_verified=False
                )
            },
        )

        assert resp.status_code == 403
        user = (await db_session.execute(select(User))).scalar_one()
        assert user.google_sub is None, "the account must be left untouched"

    async def test_an_unverified_email_cannot_create_an_account(self, client, db_session):
        resp = await client.post(
            "/api/auth/google",
            json={"credential": google_token(email="nobody@example.com", email_verified=False)},
        )

        assert resp.status_code == 403
        assert (await db_session.execute(select(User))).scalars().all() == []

    async def test_an_inactive_account_cannot_sign_in_with_google(self, client, db_session):
        await _register(client, "dave@example.com")
        user = (await db_session.execute(select(User))).scalar_one()
        user.is_active = False
        await db_session.commit()

        resp = await client.post(
            "/api/auth/google", json={"credential": google_token(email="dave@example.com")}
        )
        assert resp.status_code == 400


class TestTokenVerification:
    """Every one of these is a way in if the check is missing."""

    async def test_it_rejects_a_token_signed_by_someone_else(self, client):
        resp = await client.post(
            "/api/auth/google", json={"credential": google_token(key=OTHER_PRIVATE_PEM)}
        )
        assert resp.status_code == 401

    async def test_it_rejects_a_token_issued_to_a_different_app(self, client, db_session):
        # Google signs every app's tokens with the same keys. Without the
        # audience check, a token from any other Google site would work here.
        resp = await client.post(
            "/api/auth/google",
            json={"credential": google_token(aud="some-other-app.apps.googleusercontent.com")},
        )
        assert resp.status_code == 401
        assert (await db_session.execute(select(User))).scalars().all() == []

    async def test_it_rejects_an_expired_token(self, client):
        resp = await client.post(
            "/api/auth/google", json={"credential": google_token(expires_in=-3600)}
        )
        assert resp.status_code == 401

    async def test_it_rejects_a_token_from_the_wrong_issuer(self, client):
        resp = await client.post(
            "/api/auth/google", json={"credential": google_token(iss="https://evil.example.com")}
        )
        assert resp.status_code == 401

    async def test_it_rejects_an_unsigned_token(self, client):
        # The classic JWT confusion attack: claim alg "none" and supply no
        # signature. We pin RS256 from the header before touching any key.
        # jose refuses to *produce* an alg:none token, so build one by hand,
        # which is what an attacker would be doing anyway.
        def b64(obj):
            return base64.urlsafe_b64encode(json.dumps(obj).encode()).rstrip(b"=").decode()

        unsigned = "{}.{}.".format(
            b64({"alg": "none", "typ": "JWT", "kid": KID}),
            b64({
                "iss": "https://accounts.google.com",
                "aud": CLIENT_ID,
                "sub": "x",
                "email": "x@y.com",
                "exp": int(time.time()) + 3600,
            }),
        )
        resp = await client.post("/api/auth/google", json={"credential": unsigned})
        assert resp.status_code == 401

    async def test_it_rejects_an_unknown_signing_key(self, client):
        resp = await client.post(
            "/api/auth/google", json={"credential": google_token(kid="not-a-real-kid")}
        )
        assert resp.status_code == 401

    async def test_it_rejects_gibberish(self, client):
        resp = await client.post("/api/auth/google", json={"credential": "not-a-jwt"})
        assert resp.status_code == 401

    async def test_it_refuses_to_run_without_a_configured_client_id(self, client):
        # No audience to check against means any Google token would pass, so
        # the endpoint must fail closed rather than open.
        settings.google_client_id = ""
        resp = await client.post("/api/auth/google", json={"credential": google_token()})
        assert resp.status_code == 401

    @respx.mock
    async def test_it_refetches_the_keys_when_google_rotates(self, client, db_session):
        # Prime the cache with a key set that lacks our kid, as if Google had
        # rotated since we last looked. One forced refetch must recover.
        google_oauth._certs_cache = (time.monotonic(), {"keys": []})
        route = respx.get(google_oauth.CERTS_URL).mock(
            return_value=httpx.Response(200, json=_jwks())
        )

        resp = await client.post("/api/auth/google", json={"credential": google_token()})

        assert resp.status_code == 200, resp.text
        assert route.called


class TestPasswordInteraction:
    """A null password hash used to be impossible. Now it is not."""

    async def test_password_login_on_a_google_only_account_explains_itself(self, client):
        # Before the guard this reached bcrypt with a None hash and raised,
        # surfacing as a 500 "Login failed" with no clue what to do.
        await client.post(
            "/api/auth/google", json={"credential": google_token(email="google.only@example.com")}
        )

        resp = await client.post(
            "/api/auth/login",
            json={"email": "google.only@example.com", "password": "anything-at-all"},
        )

        assert resp.status_code == 400
        assert "Google" in resp.json()["detail"]

    async def test_a_google_user_can_set_a_first_password(self, client):
        # Their only recovery path if they ever lose the Google account.
        signin = await client.post(
            "/api/auth/google", json={"credential": google_token(email="google.only@example.com")}
        )
        headers = {"Authorization": f"Bearer {signin.json()['access_token']}"}

        resp = await client.put(
            "/api/auth/me", json={"new_password": "a-brand-new-password"}, headers=headers
        )
        assert resp.status_code == 200, resp.text
        assert resp.json()["has_password"] is True

        login = await client.post(
            "/api/auth/login",
            json={"email": "google.only@example.com", "password": "a-brand-new-password"},
        )
        assert login.status_code == 200, login.text

    async def test_a_password_user_still_needs_the_old_one(self, client):
        # The new "no current password needed" branch must not leak into
        # accounts that do have one.
        registered = await _register(client, "dave@example.com")
        headers = {"Authorization": f"Bearer {registered['access_token']}"}

        resp = await client.put(
            "/api/auth/me",
            json={"new_password": "attacker-chosen-password"},
            headers=headers,
        )
        # No current_password supplied, so the change is silently not applied.
        assert resp.status_code == 200
        still_works = await client.post(
            "/api/auth/login",
            json={"email": "dave@example.com", "password": "testpassword123"},
        )
        assert still_works.status_code == 200, "the original password must survive"


class TestProfileExposure:
    async def test_me_reports_both_sign_in_methods(self, client):
        registered = await _register(client, "dave@example.com")
        headers = {"Authorization": f"Bearer {registered['access_token']}"}

        before = await client.get("/api/auth/me", headers=headers)
        assert before.json()["has_google"] is False
        assert before.json()["has_password"] is True

        await client.post(
            "/api/auth/google", json={"credential": google_token(email="dave@example.com")}
        )
        after = await client.get("/api/auth/me", headers=headers)
        assert after.json()["has_google"] is True
        assert after.json()["avatar_url"] == "https://lh3.googleusercontent.com/a/photo"

    async def test_registration_stores_a_normalized_address(self, client, db_session):
        await _register(client, "  Mixed.Case@Example.COM  ".strip())
        user = (await db_session.execute(select(User))).scalar_one()
        assert user.email == "mixed.case@example.com"

    async def test_meta_publishes_the_client_id(self, client):
        resp = await client.get("/api/meta")
        assert resp.json()["google_client_id"] == CLIENT_ID
