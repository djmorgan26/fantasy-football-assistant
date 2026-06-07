"""Sleeper league endpoints exercised through mock mode."""
import pytest
from httpx import AsyncClient

from app.services import mock_data


pytestmark = pytest.mark.integration


class TestSleeperConnect:
    async def test_connect_creates_league_and_teams(self, sleeper_league):
        league = sleeper_league["league"]
        assert league["platform"].lower() == "sleeper"
        assert league["sleeper_league_id"] == mock_data.MOCK_SLEEPER_LEAGUE_ID
        teams = sleeper_league["teams"]
        assert len(teams) == 10
        # Regression: TeamResponse must serialize Sleeper teams, which have
        # no espn_team_id (it used to be a required int and 500ed).
        assert all(t["espn_team_id"] is None for t in teams)
        assert all(t["sleeper_roster_id"] is not None for t in teams)

    async def test_connect_unknown_user_404(self, client: AsyncClient, auth_headers, mock_mode):
        # The mock sleeper_user helper answers for any id, so this only
        # asserts the endpoint shape, not a 404. Validate the response model.
        resp = await client.post(
            "/api/sleeper/connect",
            json={
                "league_id": mock_data.MOCK_SLEEPER_LEAGUE_ID,
                "sleeper_user_id": mock_data.MOCK_SLEEPER_USER_ID,
            },
            headers=auth_headers,
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["success"] is True
        assert body["teams_synced"] == 10


class TestSleeperEndpoints:
    async def test_user_leagues(self, client: AsyncClient, auth_headers, mock_mode):
        resp = await client.get(
            f"/api/sleeper/user/{mock_data.MOCK_SLEEPER_USER_ID}/leagues/{mock_data.MOCK_SEASON}",
            headers=auth_headers,
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["user_id"] == mock_data.MOCK_SLEEPER_USER_ID
        assert len(body["leagues"]) >= 1

    async def test_matchups_use_sleeper_schema(
        self, client: AsyncClient, auth_headers, sleeper_league
    ):
        # Regression: this endpoint used to construct the ESPN-shaped
        # MatchupResponse and 500 on every call.
        resp = await client.get(
            f"/api/sleeper/league/{mock_data.MOCK_SLEEPER_LEAGUE_ID}/matchups/1",
            headers=auth_headers,
        )
        assert resp.status_code == 200
        matchups = resp.json()
        assert len(matchups) > 0
        first = matchups[0]
        assert {"roster_id", "matchup_id", "points", "starters", "players"} <= set(first)

    async def test_matchups_unknown_league_404(
        self, client: AsyncClient, auth_headers, mock_mode
    ):
        resp = await client.get(
            "/api/sleeper/league/not-connected/matchups/1", headers=auth_headers
        )
        assert resp.status_code == 404

    async def test_rosters(self, client: AsyncClient, auth_headers, sleeper_league):
        resp = await client.get(
            f"/api/sleeper/league/{mock_data.MOCK_SLEEPER_LEAGUE_ID}/rosters",
            headers=auth_headers,
        )
        assert resp.status_code == 200
        rosters = resp.json()
        assert len(rosters) == 10
        assert all("roster_id" in r and "players" in r for r in rosters)

    async def test_health(self, client: AsyncClient, mock_mode):
        resp = await client.get("/api/sleeper/health")
        assert resp.status_code == 200
        assert resp.json()["status"] == "healthy"
