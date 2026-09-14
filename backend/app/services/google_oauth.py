"""Verification of Google Identity Services ID tokens.

The browser hands us a signed JWT ("credential") from Google and we turn it
into one of our own sessions. Everything that matters happens here: the token
arrives from the client, so it is attacker-controlled until proven otherwise.

We verify it ourselves against Google's published keys rather than calling
Google's tokeninfo endpoint, which is rate limited and adds a round trip to
every sign-in.

Four checks have to pass, and each one closes a real hole:

- signature, against the JWKS at ``CERTS_URL``. Without it anyone can mint a
  token claiming to be any email.
- ``aud`` equals our own client id. Google signs tokens for every app on the
  platform with the same keys, so a token issued to some other site is
  perfectly valid; only the audience says it was meant for us.
- ``iss`` is Google.
- ``exp``/``iat``, with a little leeway for clock drift between us and Google.

``email_verified`` is checked by the caller, not here, because what to do
about an unverified email is an account-linking policy decision rather than a
question about whether the token is genuine.
"""
import asyncio
import time
from typing import Any, Dict, Optional, Tuple

import httpx
import structlog
from jose import jwt, JWTError

from app.core.config import settings

logger = structlog.get_logger()

CERTS_URL = "https://www.googleapis.com/oauth2/v3/certs"

# Google publishes both spellings and has never committed to one.
VALID_ISSUERS = ("accounts.google.com", "https://accounts.google.com")

# Google rotates signing keys every few days and serves the new key alongside
# the old one well before it starts using it, so a cache measured in hours is
# safe. An unknown `kid` forces a refetch regardless (see _key_for), which is
# what actually makes rotation safe rather than this number.
CERTS_TTL_SECONDS = 3600.0

# Tolerance for clock drift between this machine and Google's signer. Google's
# own libraries allow the same order of magnitude.
CLOCK_SKEW_SECONDS = 10

_certs_cache: Optional[Tuple[float, Dict[str, Any]]] = None
_certs_lock: Optional[Tuple[Any, asyncio.Lock]] = None


class GoogleTokenError(Exception):
    """The credential did not verify. The message is safe to log, not to show.

    Sign-in failures get a single generic message at the API boundary: telling
    a caller *which* check failed tells an attacker which one to fix next.
    """


def _lock() -> asyncio.Lock:
    # Same shape as the locks in draft_service: a module-level singleton
    # outlives the event loop it was built on, and a reused serverless
    # container can hand us a fresh loop. A lock bound to a dead loop raises
    # when awaited, so rebuild it whenever the loop changes.
    global _certs_lock
    loop = asyncio.get_running_loop()
    if _certs_lock is None or _certs_lock[0] is not loop:
        _certs_lock = (loop, asyncio.Lock())
    return _certs_lock[1]


def _cached_certs() -> Optional[Dict[str, Any]]:
    if _certs_cache is None:
        return None
    fetched_at, certs = _certs_cache
    if time.monotonic() - fetched_at > CERTS_TTL_SECONDS:
        return None
    return certs


async def _fetch_certs(newer_than: Optional[float] = None) -> Dict[str, Any]:
    """Return Google's key set, fetching it unless someone else just did.

    `newer_than` is the age of the cache the caller already looked in and
    found wanting. Without it, the double-check below would hand that same
    stale cache straight back and a key rotation would lock every user out
    until the TTL expired. With it, a caller that has seen a cache miss is
    guaranteed either a genuine fetch or a cache someone else filled after
    the miss.
    """
    global _certs_cache
    async with _lock():
        # Double-checked: several sign-ins can miss an empty cache at once,
        # and without this they would all hit Google.
        cached = _certs_cache
        if cached is not None:
            fetched_at, certs = cached
            within_ttl = time.monotonic() - fetched_at <= CERTS_TTL_SECONDS
            refetched_since = newer_than is None or fetched_at > newer_than
            if within_ttl and refetched_since:
                return certs

        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(CERTS_URL)
            response.raise_for_status()
            certs = response.json()
        _certs_cache = (time.monotonic(), certs)
        return certs


async def _key_for(kid: str) -> Dict[str, Any]:
    """The JWKS entry for `kid`, refetching once if we have not seen it.

    A miss is the normal signal that Google has rotated to a key minted after
    our cache was filled, so one forced refetch turns rotation into a single
    slow request rather than an outage. It is also the reason an attacker
    cannot use a made-up `kid` to spin us: the refetch is bounded at one, and a
    key that is still missing afterwards is an error, not a retry.
    """
    seen_at: Optional[float] = None
    cached = _certs_cache
    if cached is not None and _cached_certs() is not None:
        seen_at = cached[0]
        for key in cached[1].get("keys", []):
            if key.get("kid") == kid:
                return key

    certs = await _fetch_certs(newer_than=seen_at)
    for key in certs.get("keys", []):
        if key.get("kid") == kid:
            return key

    raise GoogleTokenError(f"no Google signing key matches kid {kid!r}")


def clear_certs_cache() -> None:
    """Drop the cached JWKS. Used by tests, which must not share Google's keys."""
    global _certs_cache, _certs_lock
    _certs_cache = None
    _certs_lock = None


async def verify_google_id_token(credential: str) -> Dict[str, Any]:
    """Verify a Google ID token and return its claims.

    Raises GoogleTokenError for anything that fails to verify.
    """
    if not settings.google_client_id:
        # Without a configured audience there is nothing to check `aud`
        # against, and a token signed for any other Google app would sail
        # through. Refusing is the only safe behaviour.
        raise GoogleTokenError("GOOGLE_CLIENT_ID is not configured")

    if not credential or not isinstance(credential, str):
        raise GoogleTokenError("credential is missing")

    try:
        header = jwt.get_unverified_header(credential)
    except JWTError as exc:
        raise GoogleTokenError(f"malformed credential: {exc}") from exc

    kid = header.get("kid")
    if not kid:
        raise GoogleTokenError("credential has no kid")

    # Pin the algorithm to what Google actually uses. Reading it from the
    # token's own header is the classic JWT confusion bug: a token could then
    # nominate "none", or an HMAC algorithm keyed on the public key.
    if header.get("alg") != "RS256":
        raise GoogleTokenError(f"unexpected alg {header.get('alg')!r}")

    key = await _key_for(kid)

    try:
        claims = jwt.decode(
            credential,
            key,
            algorithms=["RS256"],
            audience=settings.google_client_id,
            issuer=VALID_ISSUERS,
            options={"leeway": CLOCK_SKEW_SECONDS},
        )
    except JWTError as exc:
        raise GoogleTokenError(f"credential did not verify: {exc}") from exc

    if not claims.get("sub"):
        raise GoogleTokenError("credential has no subject")
    if not claims.get("email"):
        raise GoogleTokenError("credential has no email")

    return claims
