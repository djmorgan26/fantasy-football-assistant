"""League endpoints (ESPN platform) exercised through mock mode."""
import pytest
from httpx import AsyncClient

from app.services import mock_data


pytestmark = pytest.mark.integration


class TestConnectLeague:
    async def test_connect_creates_league_and_teams(self, espn_league):
        league = espn_league["league"]
        assert league["espn_league_id"] == mock_data.MOCK_ESPN_LEAGUE_ID
        assert league["is_active"] is True
        assert len(espn_league["teams"]) == league["size"] == 10

    async def test_connect_is_idempotent(self, client: AsyncClient, auth_headers, espn_league):
        resp = await client.post(
            "/api/leagues/connect",
            json={"league_id": mock_data.MOCK_ESPN_LEAGUE_ID},
            headers=auth_headers,
        )
        assert resp.status_code == 200
        assert resp.json()["league"]["id"] == espn_league["league"]["id"]

    async def test_connect_requires_auth(self, client: AsyncClient):
        resp = await client.post(
            "/api/leagues/connect", json={"league_id": 123}
        )
        assert resp.status_code == 401


class TestListAndGet:
    async def test_list_leagues(self, client: AsyncClient, auth_headers, espn_league):
        resp = await client.get("/api/leagues/", headers=auth_headers)
        assert resp.status_code == 200
        leagues = resp.json()
        assert len(leagues) == 1
        assert leagues[0]["id"] == espn_league["league"]["id"]

    async def test_get_league(self, client: AsyncClient, auth_headers, espn_league):
        lid = espn_league["league"]["id"]
        resp = await client.get(f"/api/leagues/{lid}", headers=auth_headers)
        assert resp.status_code == 200
        assert resp.json()["name"] == espn_league["league"]["name"]

    async def test_get_unknown_league_404(self, client: AsyncClient, auth_headers):
        resp = await client.get("/api/leagues/99999", headers=auth_headers)
        assert resp.status_code == 404

    async def test_other_users_league_is_hidden(
        self, client: AsyncClient, espn_league
    ):
        # Second user must not see (or fetch) the first user's league.
        other = await client.post(
            "/api/auth/register",
            json={"email": "other@example.com", "password": "password123"},
        )
        headers = {"Authorization": f"Bearer {other.json()['access_token']}"}
        listing = await client.get("/api/leagues/", headers=headers)
        assert listing.json() == []
        lid = espn_league["league"]["id"]
        resp = await client.get(f"/api/leagues/{lid}", headers=headers)
        assert resp.status_code == 404


class TestSyncAndDisconnect:
    async def test_sync(self, client: AsyncClient, auth_headers, espn_league):
        lid = espn_league["league"]["id"]
        resp = await client.post(f"/api/leagues/{lid}/sync", headers=auth_headers)
        assert resp.status_code == 200
        assert resp.json()["success"] is True

    async def test_disconnect_marks_inactive(
        self, client: AsyncClient, auth_headers, espn_league
    ):
        lid = espn_league["league"]["id"]
        resp = await client.delete(f"/api/leagues/{lid}", headers=auth_headers)
        assert resp.status_code == 200
        # League disappears from the active list
        listing = await client.get("/api/leagues/", headers=auth_headers)
        assert all(l["id"] != lid for l in listing.json())


class TestMatchupsAndBudgets:
    async def test_matchups_current_week(
        self, client: AsyncClient, auth_headers, espn_league
    ):
        lid = espn_league["league"]["id"]
        resp = await client.get(f"/api/leagues/{lid}/matchups", headers=auth_headers)
        assert resp.status_code == 200
        matchups = resp.json()
        assert len(matchups) > 0
        first = matchups[0]
        assert {"home_team_name", "away_team_name", "home_score", "away_score"} <= set(first)

    async def test_matchups_specific_week(
        self, client: AsyncClient, auth_headers, espn_league
    ):
        lid = espn_league["league"]["id"]
        resp = await client.get(
            f"/api/leagues/{lid}/matchups?week=1", headers=auth_headers
        )
        assert resp.status_code == 200
        assert all(m["week"] == 1 for m in resp.json())

    async def test_waiver_budgets(
        self, client: AsyncClient, auth_headers, espn_league
    ):
        lid = espn_league["league"]["id"]
        resp = await client.get(
            f"/api/leagues/{lid}/waiver-budgets", headers=auth_headers
        )
        assert resp.status_code == 200
        budgets = resp.json()
        assert len(budgets) == 10
