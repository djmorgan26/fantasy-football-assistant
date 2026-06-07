"""Strategic suggestions and weekly recap on both platforms."""
import pytest
from httpx import AsyncClient


pytestmark = pytest.mark.integration


class TestSuggestions:
    async def test_espn_suggestions(self, client: AsyncClient, auth_headers, espn_league):
        league_id = espn_league["league"]["id"]
        team_id = espn_league["teams"][0]["id"]
        resp = await client.get(
            f"/api/suggestions/{league_id}/{team_id}", headers=auth_headers
        )
        assert resp.status_code == 200, resp.text
        suggestions = resp.json()
        assert isinstance(suggestions, list)
        assert len(suggestions) > 0
        first = suggestions[0]
        assert {"type", "priority", "title", "description"} <= set(first)

    async def test_sleeper_suggestions(self, client: AsyncClient, auth_headers, sleeper_league):
        # Regression: suggestions used to route Sleeper leagues into the ESPN
        # client and 500.
        league_id = sleeper_league["league"]["id"]
        team_id = sleeper_league["teams"][0]["id"]
        resp = await client.get(
            f"/api/suggestions/{league_id}/{team_id}", headers=auth_headers
        )
        assert resp.status_code == 200, resp.text
        assert len(resp.json()) > 0

    async def test_team_not_in_league_404(
        self, client: AsyncClient, auth_headers, espn_league, sleeper_league
    ):
        # Regression: team_id is the DB id and must belong to the league.
        espn_id = espn_league["league"]["id"]
        sleeper_team = sleeper_league["teams"][0]["id"]
        resp = await client.get(
            f"/api/suggestions/{espn_id}/{sleeper_team}", headers=auth_headers
        )
        assert resp.status_code == 404

    async def test_unknown_league_404(self, client: AsyncClient, auth_headers, mock_mode):
        resp = await client.get("/api/suggestions/4242/1", headers=auth_headers)
        assert resp.status_code == 404

    async def test_health(self, client: AsyncClient):
        resp = await client.get("/api/suggestions/health")
        assert resp.status_code == 200
        assert "llm_available" in resp.json()


class TestWeeklyRecap:
    async def test_espn_recap(self, client: AsyncClient, auth_headers, espn_league):
        lid = espn_league["league"]["id"]
        resp = await client.get(
            f"/api/recap/league/{lid}/week/1", headers=auth_headers
        )
        assert resp.status_code == 200, resp.text
        body = resp.json()
        assert body["recap"]
        assert body["week"] == 1

    async def test_sleeper_recap(self, client: AsyncClient, auth_headers, sleeper_league):
        lid = sleeper_league["league"]["id"]
        resp = await client.get(
            f"/api/recap/league/{lid}/week/1", headers=auth_headers
        )
        assert resp.status_code == 200, resp.text
        assert resp.json()["recap"]

    async def test_unknown_league_404(self, client: AsyncClient, auth_headers, mock_mode):
        resp = await client.get("/api/recap/league/4242/week/1", headers=auth_headers)
        assert resp.status_code == 404

    async def test_health(self, client: AsyncClient):
        resp = await client.get("/api/recap/health")
        assert resp.status_code == 200
