"""Trade analysis and persistence."""
import pytest
from httpx import AsyncClient


pytestmark = pytest.mark.integration


async def _roster_player_ids(client, headers, team_id):
    resp = await client.get(f"/api/teams/{team_id}/roster", headers=headers)
    assert resp.status_code == 200
    return [p["player_id"] for p in resp.json()["roster"]]


class TestTradeAnalysis:
    async def test_analyze_valid_trade(self, client: AsyncClient, auth_headers, espn_league):
        t1, t2 = espn_league["teams"][0], espn_league["teams"][1]
        give = (await _roster_player_ids(client, auth_headers, t1["id"]))[:1]
        receive = (await _roster_player_ids(client, auth_headers, t2["id"]))[:1]

        resp = await client.post(
            "/api/trades/analyze",
            json={
                "league_id": espn_league["league"]["id"],
                "proposing_team_id": t1["id"],
                "receiving_team_id": t2["id"],
                # Regression: mock/string player ids used to be rejected by a
                # List[int] schema, breaking the analyzer in the demo.
                "give_players": give,
                "receive_players": receive,
            },
            headers=auth_headers,
        )
        assert resp.status_code == 200, resp.text
        body = resp.json()
        assert body["is_valid"] is True
        # Regression: fairness used to be a constant 50.0 because projected
        # points were read from the wrong field and always 0.
        assert body["fairness_score"] is not None
        assert body["player_details"]["give"]
        assert body["player_details"]["receive"]
        give_details = list(body["player_details"]["give"].values())[0]
        assert give_details["projected_points"] > 0

    async def test_analyze_player_not_on_roster(
        self, client: AsyncClient, auth_headers, espn_league
    ):
        t1, t2 = espn_league["teams"][0], espn_league["teams"][1]
        give = (await _roster_player_ids(client, auth_headers, t1["id"]))[:1]
        resp = await client.post(
            "/api/trades/analyze",
            json={
                "league_id": espn_league["league"]["id"],
                "proposing_team_id": t1["id"],
                "receiving_team_id": t2["id"],
                "give_players": give,
                "receive_players": ["not-a-real-player"],
            },
            headers=auth_headers,
        )
        assert resp.status_code == 200
        assert resp.json()["is_valid"] is False

    async def test_analyze_same_team_rejected(
        self, client: AsyncClient, auth_headers, espn_league
    ):
        t1 = espn_league["teams"][0]
        resp = await client.post(
            "/api/trades/analyze",
            json={
                "league_id": espn_league["league"]["id"],
                "proposing_team_id": t1["id"],
                "receiving_team_id": t1["id"],
                "give_players": ["p0001"],
                "receive_players": ["p0002"],
            },
            headers=auth_headers,
        )
        assert resp.status_code == 422

    async def test_analyze_unknown_league_404(self, client: AsyncClient, auth_headers, mock_mode):
        resp = await client.post(
            "/api/trades/analyze",
            json={
                "league_id": 4242,
                "proposing_team_id": 1,
                "receiving_team_id": 2,
                "give_players": ["p0001"],
                "receive_players": ["p0002"],
            },
            headers=auth_headers,
        )
        assert resp.status_code == 404

    async def test_empty_players_rejected(self, client: AsyncClient, auth_headers, espn_league):
        resp = await client.post(
            "/api/trades/analyze",
            json={
                "league_id": espn_league["league"]["id"],
                "proposing_team_id": 1,
                "receiving_team_id": 2,
                "give_players": [],
                "receive_players": ["p0002"],
            },
            headers=auth_headers,
        )
        assert resp.status_code == 422


class TestTradePersistence:
    async def test_create_list_get(self, client: AsyncClient, auth_headers, espn_league):
        t1, t2 = espn_league["teams"][0], espn_league["teams"][1]
        give = (await _roster_player_ids(client, auth_headers, t1["id"]))[:1]
        receive = (await _roster_player_ids(client, auth_headers, t2["id"]))[:1]

        created = await client.post(
            "/api/trades/",
            json={
                "league_id": espn_league["league"]["id"],
                "proposing_team_id": t1["id"],
                "receiving_team_id": t2["id"],
                "give_players": give,
                "receive_players": receive,
            },
            headers=auth_headers,
        )
        assert created.status_code == 200, created.text
        trade = created.json()
        assert trade["status"] == "pending"
        assert trade["proposed_players"]["give"] == give
        assert trade["expires_at"] is not None

        listing = await client.get("/api/trades/", headers=auth_headers)
        assert listing.status_code == 200
        assert any(t["id"] == trade["id"] for t in listing.json())

        single = await client.get(f"/api/trades/{trade['id']}", headers=auth_headers)
        assert single.status_code == 200
        assert single.json()["id"] == trade["id"]

    async def test_get_unknown_trade_404(self, client: AsyncClient, auth_headers, mock_mode):
        resp = await client.get("/api/trades/9999", headers=auth_headers)
        assert resp.status_code == 404
