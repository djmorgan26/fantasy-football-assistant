"""Draft tools: generic rankings, league value boards, live assist."""
import pytest
from httpx import AsyncClient


pytestmark = pytest.mark.integration


class TestGenericRankings:
    async def test_rankings(self, client: AsyncClient, auth_headers, mock_mode):
        resp = await client.get(
            "/api/draft/rankings?scoring_type=ppr&team_count=10",
            headers=auth_headers,
        )
        assert resp.status_code == 200
        body = resp.json()
        players = body["players"]
        assert len(players) > 0
        first = players[0]
        assert {"player_id", "name", "position"} <= set(first)

    async def test_rankings_requires_auth(self, client: AsyncClient, mock_mode):
        resp = await client.get("/api/draft/rankings")
        assert resp.status_code == 401


class TestLeagueValueBoard:
    async def test_espn_value_board(self, client: AsyncClient, auth_headers, espn_league):
        lid = espn_league["league"]["id"]
        resp = await client.get(f"/api/draft/value-board/{lid}", headers=auth_headers)
        assert resp.status_code == 200
        assert len(resp.json()["players"]) > 0

    async def test_sleeper_value_board(self, client: AsyncClient, auth_headers, sleeper_league):
        lid = sleeper_league["league"]["id"]
        resp = await client.get(f"/api/draft/value-board/{lid}", headers=auth_headers)
        assert resp.status_code == 200
        assert len(resp.json()["players"]) > 0

    async def test_unknown_league_404(self, client: AsyncClient, auth_headers, mock_mode):
        resp = await client.get("/api/draft/value-board/4242", headers=auth_headers)
        assert resp.status_code == 404


class TestDraftAssist:
    async def test_espn_assist(self, client: AsyncClient, auth_headers, espn_league):
        lid = espn_league["league"]["id"]
        resp = await client.get(f"/api/draft/assist/{lid}", headers=auth_headers)
        assert resp.status_code == 200

    async def test_sleeper_assist(self, client: AsyncClient, auth_headers, sleeper_league):
        lid = sleeper_league["league"]["id"]
        resp = await client.get(f"/api/draft/assist/{lid}", headers=auth_headers)
        assert resp.status_code == 200


class TestDraftHealth:
    async def test_health(self, client: AsyncClient, mock_mode):
        resp = await client.get("/api/draft/health")
        assert resp.status_code == 200
