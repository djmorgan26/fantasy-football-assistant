"""
Operational surface: health probes, request ids, access logging, security
headers, and the handler that keeps a crash from reaching a browser as a stack
trace.

These are the things that only matter once the app is live, which is exactly
why they are easy to ship broken — nothing in normal development exercises
them.
"""
import asyncio

import pytest
from httpx import ASGITransport, AsyncClient

from app.core.observability import REQUEST_ID_HEADER, build_info

pytestmark = pytest.mark.integration


class TestLiveness:
    async def test_live_reports_up(self, client: AsyncClient):
        resp = await client.get("/health/live")
        assert resp.status_code == 200

        body = resp.json()
        assert body["status"] == "ok"
        assert body["uptime_seconds"] >= 0
        assert body["version"]

    async def test_health_is_an_alias_for_live(self, client: AsyncClient):
        """Existing deploy config points at /health; it must keep working."""
        alias = await client.get("/health")
        assert alias.status_code == 200
        assert alias.json()["status"] == "ok"

    async def test_liveness_does_not_touch_the_database(self, client: AsyncClient, monkeypatch):
        """A database blip must not get a healthy container restarted."""
        def explode(*args, **kwargs):
            raise AssertionError("liveness touched the database")

        monkeypatch.setattr("app.api.health.SessionLocal", explode)
        assert (await client.get("/health/live")).status_code == 200

    async def test_needs_no_auth(self, client: AsyncClient):
        assert (await client.get("/health/live")).status_code == 200
        assert (await client.get("/health/ready")).status_code in (200, 503)


class TestReadiness:
    async def test_ready_when_the_database_answers(self, client: AsyncClient):
        resp = await client.get("/health/ready")
        assert resp.status_code == 200

        body = resp.json()
        assert body["status"] == "ready"
        assert body["checks"]["database"]["status"] == "ok"
        assert body["checks"]["database"]["latency_ms"] >= 0

    async def test_reports_feature_availability_without_gating_on_it(
        self, client: AsyncClient
    ):
        """No model key in tests, yet the instance is still fit for traffic."""
        body = (await client.get("/health/ready")).json()
        assert body["features"]["llm"] == "not_configured"
        assert body["status"] == "ready"

    async def test_503_when_the_database_is_down(self, client: AsyncClient, monkeypatch):
        async def broken_check():
            return {"status": "error", "error": "OperationalError"}

        monkeypatch.setattr("app.api.health._check_database", broken_check)

        resp = await client.get("/health/ready")
        assert resp.status_code == 503
        assert resp.json()["status"] == "not_ready"

    async def test_a_wedged_database_times_out_rather_than_hanging(
        self, client: AsyncClient, monkeypatch
    ):
        """A probe that never returns is worse than one that fails."""
        monkeypatch.setattr("app.api.health.DB_CHECK_TIMEOUT_SECONDS", 0.01)

        class Hanging:
            async def __aenter__(self):
                await asyncio.sleep(5)

            async def __aexit__(self, *args):
                return False

        monkeypatch.setattr("app.api.health.SessionLocal", lambda: Hanging())

        resp = await client.get("/health/ready")
        assert resp.status_code == 503
        assert resp.json()["checks"]["database"]["status"] == "timeout"


class TestRequestIds:
    async def test_every_response_carries_one(self, client: AsyncClient):
        resp = await client.get("/health/live")
        assert resp.headers[REQUEST_ID_HEADER]

    async def test_an_incoming_id_is_kept_so_a_trace_survives_a_proxy(
        self, client: AsyncClient
    ):
        resp = await client.get("/health/live", headers={REQUEST_ID_HEADER: "abc123"})
        assert resp.headers[REQUEST_ID_HEADER] == "abc123"

    async def test_ids_differ_between_requests(self, client: AsyncClient):
        first = (await client.get("/health/live")).headers[REQUEST_ID_HEADER]
        second = (await client.get("/health/live")).headers[REQUEST_ID_HEADER]
        assert first != second

    async def test_timing_is_reported(self, client: AsyncClient):
        resp = await client.get("/health/live")
        assert resp.headers["Server-Timing"].startswith("app;dur=")


class TestSecurityHeaders:
    @pytest.mark.parametrize(
        "header,expected",
        [
            ("X-Content-Type-Options", "nosniff"),
            ("X-Frame-Options", "DENY"),
            ("Referrer-Policy", "strict-origin-when-cross-origin"),
        ],
    )
    async def test_present_on_every_response(self, client: AsyncClient, header, expected):
        resp = await client.get("/health/live")
        assert resp.headers[header] == expected

    async def test_present_on_error_responses_too(self, client: AsyncClient):
        resp = await client.get("/api/leagues/999999")
        assert resp.status_code in (401, 404)
        assert resp.headers["X-Content-Type-Options"] == "nosniff"


class TestUnhandledErrors:
    async def test_a_crash_becomes_json_not_a_stack_trace(self):
        """The frontend reads `detail`; a 500 has to speak the same shape."""
        from fastapi import FastAPI
        from app.core.observability import install_observability

        app = FastAPI()
        install_observability(app)

        @app.get("/boom")
        async def boom():
            raise RuntimeError("a secret internal detail")

        transport = ASGITransport(app=app, raise_app_exceptions=False)
        async with AsyncClient(transport=transport, base_url="http://testserver") as ac:
            resp = await ac.get("/boom")

        assert resp.status_code == 500
        body = resp.json()
        assert "detail" in body
        assert body["request_id"]
        # The internal message must not reach the client.
        assert "secret internal detail" not in resp.text


class TestBuildInfo:
    def test_reports_dev_when_no_commit_is_injected(self, monkeypatch):
        monkeypatch.delenv("VERCEL_GIT_COMMIT_SHA", raising=False)
        monkeypatch.delenv("GIT_COMMIT_SHA", raising=False)
        assert build_info()["commit"] == "dev"

    def test_shortens_an_injected_commit(self, monkeypatch):
        monkeypatch.setenv("VERCEL_GIT_COMMIT_SHA", "a" * 40)
        assert build_info()["commit"] == "a" * 12

    def test_names_the_environment(self, monkeypatch):
        monkeypatch.setenv("VERCEL_ENV", "production")
        assert build_info()["environment"] == "production"


class TestMeta:
    async def test_meta_is_public_and_flags_mock_mode(self, client: AsyncClient):
        resp = await client.get("/api/meta")
        assert resp.status_code == 200
        assert resp.json()["mock_mode"] is False

    async def test_meta_never_leaks_demo_credentials_in_real_mode(self, client: AsyncClient):
        assert "demo_credentials" not in (await client.get("/api/meta")).json()

    async def test_meta_hands_out_demo_credentials_only_in_mock_mode(
        self, client: AsyncClient, mock_mode
    ):
        body = (await client.get("/api/meta")).json()
        assert body["mock_mode"] is True
        assert body["demo_credentials"]["email"]
