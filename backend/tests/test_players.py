"""Player search and availability endpoints."""
import pytest
from httpx import AsyncClient


pytestmark = pytest.mark.integration


class TestAvailablePlayers:
    async def test_available_players(self, client: AsyncClient, auth_headers, espn_league):
        lid = espn_league["league"]["id"]
        resp = await client.get(
            f"/api/players/league/{lid}/available", headers=auth_headers
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["total_count"] == len(body["players"]) > 0

    async def test_available_players_position_filter(
        self, client: AsyncClient, auth_headers, espn_league
    ):
        lid = espn_league["league"]["id"]
        # Derive a position present in the pool, then filter by it.
        all_resp = await client.get(
            f"/api/players/league/{lid}/available", headers=auth_headers
        )
        position = all_resp.json()["players"][0]["position_name"]
        resp = await client.get(
            f"/api/players/league/{lid}/available?position={position}",
            headers=auth_headers,
        )
        assert resp.status_code == 200
        players = resp.json()["players"]
        assert players
        assert all(p["position_name"] == position for p in players)

    async def test_position_filter_excludes_other_positions(
        self, client: AsyncClient, auth_headers, espn_league
    ):
        lid = espn_league["league"]["id"]
        resp = await client.get(
            f"/api/players/league/{lid}/available?position=NOPE", headers=auth_headers
        )
        assert resp.status_code == 200
        assert resp.json()["players"] == []

    async def test_unknown_league_404(self, client: AsyncClient, auth_headers, mock_mode):
        resp = await client.get(
            "/api/players/league/4242/available", headers=auth_headers
        )
        assert resp.status_code == 404


class TestPlayerSearch:
    async def test_search(self, client: AsyncClient, auth_headers, espn_league):
        resp = await client.post(
            "/api/players/search",
            json={"league_id": espn_league["league"]["id"], "search_term": "a"},
            headers=auth_headers,
        )
        assert resp.status_code == 200
        body = resp.json()
        assert "players" in body and "total_count" in body

    async def test_search_requires_auth(self, client: AsyncClient):
        resp = await client.post("/api/players/search", json={"league_id": 1})
        assert resp.status_code == 401
