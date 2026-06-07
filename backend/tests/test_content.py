"""Content engine: voice profiles, narratives, generation, personas."""
import pytest
from httpx import AsyncClient


pytestmark = pytest.mark.integration


class TestContentProfile:
    async def test_get_profile_autoseeds(self, client: AsyncClient, auth_headers, espn_league):
        lid = espn_league["league"]["id"]
        resp = await client.get(f"/api/content/{lid}/profile", headers=auth_headers)
        assert resp.status_code == 200
        profile = resp.json()
        assert profile["voice_guide"]
        assert isinstance(profile["personas"], list)

    async def test_update_profile(self, client: AsyncClient, auth_headers, espn_league):
        lid = espn_league["league"]["id"]
        resp = await client.put(
            f"/api/content/{lid}/profile",
            json={"voice_guide": "Be extremely kind and wholesome."},
            headers=auth_headers,
        )
        assert resp.status_code == 200
        assert resp.json()["voice_guide"] == "Be extremely kind and wholesome."

        again = await client.get(f"/api/content/{lid}/profile", headers=auth_headers)
        assert again.json()["voice_guide"] == "Be extremely kind and wholesome."

    async def test_personas_autofill(self, client: AsyncClient, auth_headers, espn_league):
        lid = espn_league["league"]["id"]
        resp = await client.post(
            f"/api/content/{lid}/personas/auto-fill", headers=auth_headers
        )
        assert resp.status_code == 200
        personas = resp.json()["personas"]
        assert len(personas) > 0
        assert all("team_name" in p for p in personas)


class TestNarrative:
    async def test_espn_narrative(self, client: AsyncClient, auth_headers, espn_league):
        lid = espn_league["league"]["id"]
        resp = await client.get(
            f"/api/content/{lid}/narrative/week/1", headers=auth_headers
        )
        assert resp.status_code == 200

    async def test_sleeper_narrative(self, client: AsyncClient, auth_headers, sleeper_league):
        lid = sleeper_league["league"]["id"]
        resp = await client.get(
            f"/api/content/{lid}/narrative/week/1", headers=auth_headers
        )
        assert resp.status_code == 200


class TestGeneration:
    @pytest.mark.parametrize("content_type", [
        "weekly_recap", "power_rankings", "awards", "season_recap",
    ])
    async def test_generate_without_llm_falls_back(
        self, client: AsyncClient, auth_headers, espn_league, content_type
    ):
        # No GROQ key in tests: generation must still return 200 with the
        # data-driven fallback, never a 500.
        lid = espn_league["league"]["id"]
        resp = await client.post(
            f"/api/content/{lid}/generate",
            json={"content_type": content_type, "week": 1},
            headers=auth_headers,
        )
        assert resp.status_code == 200, resp.text
        body = resp.json()
        assert body["content"]
        assert body["content_type"] == content_type

    async def test_generate_invalid_type_422(
        self, client: AsyncClient, auth_headers, espn_league
    ):
        lid = espn_league["league"]["id"]
        resp = await client.post(
            f"/api/content/{lid}/generate",
            json={"content_type": "sonnet", "week": 1},
            headers=auth_headers,
        )
        assert resp.status_code == 422

    async def test_health(self, client: AsyncClient, mock_mode):
        resp = await client.get("/api/content/health")
        assert resp.status_code == 200
