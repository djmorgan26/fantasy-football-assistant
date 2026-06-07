"""Team endpoints: listing, details, claiming, and rosters on both platforms."""
import pytest
from httpx import AsyncClient


pytestmark = pytest.mark.integration


class TestTeamListing:
    async def test_list_league_teams(self, client: AsyncClient, auth_headers, espn_league):
        teams = espn_league["teams"]
        assert len(teams) == 10
        assert all(t["name"] for t in teams)

    async def test_get_single_team(self, client: AsyncClient, auth_headers, espn_league):
        team = espn_league["teams"][0]
        resp = await client.get(f"/api/teams/{team['id']}", headers=auth_headers)
        assert resp.status_code == 200
        assert resp.json()["name"] == team["name"]

    async def test_get_unknown_team_404(self, client: AsyncClient, auth_headers, mock_mode):
        resp = await client.get("/api/teams/9999", headers=auth_headers)
        assert resp.status_code == 404


class TestClaimTeam:
    async def test_claim_and_switch(self, client: AsyncClient, auth_headers, espn_league):
        t1, t2 = espn_league["teams"][0], espn_league["teams"][1]

        resp = await client.put(f"/api/teams/{t1['id']}/claim", headers=auth_headers)
        assert resp.status_code == 200
        assert resp.json()["owner_user_id"] is not None

        # Claiming a second team must release the first.
        resp = await client.put(f"/api/teams/{t2['id']}/claim", headers=auth_headers)
        assert resp.status_code == 200
        first = await client.get(f"/api/teams/{t1['id']}", headers=auth_headers)
        assert first.json()["owner_user_id"] is None

    async def test_claim_other_users_team_forbidden(
        self, client: AsyncClient, espn_league
    ):
        other = await client.post(
            "/api/auth/register",
            json={"email": "intruder@example.com", "password": "password123"},
        )
        headers = {"Authorization": f"Bearer {other.json()['access_token']}"}
        team = espn_league["teams"][0]
        resp = await client.put(f"/api/teams/{team['id']}/claim", headers=headers)
        assert resp.status_code == 403


class TestEspnRoster:
    async def test_roster_shape(self, client: AsyncClient, auth_headers, espn_league):
        team = espn_league["teams"][0]
        resp = await client.get(f"/api/teams/{team['id']}/roster", headers=auth_headers)
        assert resp.status_code == 200
        body = resp.json()
        assert body["team_id"] == team["id"]
        players = body["roster"]
        assert len(players) >= 9
        first = players[0]
        assert {"player_id", "full_name", "position_name", "lineup_slot_name"} <= set(first)
        # Regression: trade analysis needs per-player point totals on the
        # roster payload (used to read raw ESPN stat dicts and always got 0).
        assert any((p.get("projected_points") or 0) > 0 for p in players)

    async def test_roster_specific_week(self, client: AsyncClient, auth_headers, espn_league):
        team = espn_league["teams"][0]
        resp = await client.get(
            f"/api/teams/{team['id']}/roster?week=2", headers=auth_headers
        )
        assert resp.status_code == 200
        assert resp.json()["week"] == 2


class TestSleeperRoster:
    async def test_roster_resolves_player_names(
        self, client: AsyncClient, auth_headers, sleeper_league
    ):
        # Regression: this endpoint used to route Sleeper teams into the ESPN
        # client (league.espn_league_id is None) and 500.
        team = sleeper_league["teams"][0]
        resp = await client.get(f"/api/teams/{team['id']}/roster", headers=auth_headers)
        assert resp.status_code == 200
        players = resp.json()["roster"]
        assert len(players) > 0
        # Names must be resolved from the players payload, not raw ids.
        assert all(p["full_name"] and not p["full_name"].startswith("p0") for p in players)
        # Starters come first, bench afterwards.
        slots = [p["lineup_slot_name"] for p in players]
        if "BENCH" in slots:
            first_bench = slots.index("BENCH")
            assert all(s == "BENCH" for s in slots[first_bench:])

    async def test_claim_sleeper_team(self, client: AsyncClient, auth_headers, sleeper_league):
        team = sleeper_league["teams"][0]
        resp = await client.put(f"/api/teams/{team['id']}/claim", headers=auth_headers)
        assert resp.status_code == 200
