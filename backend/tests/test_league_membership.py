"""Two managers, one league.

This is the regression suite for the bug that locked a real user out of their
own league: both connect endpoints looked the league up by its *platform* id
across all users, then reassigned `owner_user_id` to whoever had just
connected. The second manager to link an ESPN or Sleeper league took it from
the first, who got "League not found or access denied" on every page after
that, the board included.
"""
import pytest
from httpx import AsyncClient

pytestmark = pytest.mark.integration

BODY = (
    "Somebody in this league started a kicker on bye and still won by thirty. "
    "I would like to speak to the commissioner about it."
)


async def _second_user(client: AsyncClient) -> dict:
    resp = await client.post(
        "/api/auth/register",
        json={
            "email": "leaguemate@example.com",
            "password": "testpassword123",
            "full_name": "League Mate",
        },
    )
    assert resp.status_code == 200, resp.text
    return {"Authorization": f"Bearer {resp.json()['access_token']}"}


class TestEspnConnect:
    async def test_second_manager_does_not_steal_the_league(
        self, client: AsyncClient, auth_headers, espn_league
    ):
        from app.services import mock_data

        lid = espn_league["league"]["id"]
        other = await _second_user(client)

        resp = await client.post(
            "/api/leagues/connect",
            json={"league_id": mock_data.MOCK_ESPN_LEAGUE_ID},
            headers=other,
        )
        assert resp.status_code == 200, resp.text
        # Same row, not a second copy of the league.
        assert resp.json()["league"]["id"] == lid

        # The first manager still has it.
        assert (await client.get(f"/api/leagues/{lid}", headers=auth_headers)).status_code == 200
        mine = await client.get("/api/leagues/", headers=auth_headers)
        assert [lg["id"] for lg in mine.json()] == [lid]

        # And so does the second.
        theirs = await client.get("/api/leagues/", headers=other)
        assert [lg["id"] for lg in theirs.json()] == [lid]

    async def test_both_managers_post_to_one_board(
        self, client: AsyncClient, auth_headers, espn_league
    ):
        from app.services import mock_data

        lid = espn_league["league"]["id"]
        other = await _second_user(client)
        await client.post(
            "/api/leagues/connect",
            json={"league_id": mock_data.MOCK_ESPN_LEAGUE_ID},
            headers=other,
        )

        posted = await client.post(
            f"/api/board/{lid}/posts", json={"body": BODY}, headers=other
        )
        assert posted.status_code == 201, posted.text
        assert posted.json()["author_name"] == "League Mate"

        # The owner sees the leaguemate's post, and it is not theirs.
        feed = await client.get(f"/api/board/{lid}/posts", headers=auth_headers)
        assert [p["id"] for p in feed.json()] == [posted.json()["id"]]
        assert feed.json()[0]["is_mine"] is False

    async def test_leaving_does_not_disconnect_it_for_the_owner(
        self, client: AsyncClient, auth_headers, espn_league
    ):
        from app.services import mock_data

        lid = espn_league["league"]["id"]
        other = await _second_user(client)
        await client.post(
            "/api/leagues/connect",
            json={"league_id": mock_data.MOCK_ESPN_LEAGUE_ID},
            headers=other,
        )

        assert (await client.delete(f"/api/leagues/{lid}", headers=other)).status_code == 200

        # Gone for the one who left, untouched for the owner.
        assert (await client.get(f"/api/leagues/{lid}", headers=other)).status_code == 404
        still_mine = await client.get(f"/api/leagues/{lid}", headers=auth_headers)
        assert still_mine.status_code == 200
        assert still_mine.json()["is_active"] is True


class TestSleeperConnect:
    async def test_second_manager_does_not_steal_the_league(
        self, client: AsyncClient, auth_headers, sleeper_league
    ):
        from app.services import mock_data

        lid = sleeper_league["league"]["id"]
        other = await _second_user(client)

        resp = await client.post(
            "/api/sleeper/connect",
            json={
                "league_id": mock_data.MOCK_SLEEPER_LEAGUE_ID,
                "sleeper_user_id": mock_data.MOCK_SLEEPER_USER_ID,
            },
            headers=other,
        )
        assert resp.status_code == 200, resp.text
        assert resp.json()["league_id"] == lid

        assert (await client.get(f"/api/leagues/{lid}", headers=auth_headers)).status_code == 200
        assert (await client.get(f"/api/leagues/{lid}", headers=other)).status_code == 200


class TestOutsiders:
    async def test_a_stranger_still_gets_404(
        self, client: AsyncClient, auth_headers, espn_league
    ):
        """Membership widens access to leaguemates, not to everyone."""
        lid = espn_league["league"]["id"]
        stranger = await _second_user(client)

        for path in (
            f"/api/leagues/{lid}",
            f"/api/board/{lid}/posts",
            f"/api/teams/league/{lid}",
        ):
            resp = await client.get(path, headers=stranger)
            assert resp.status_code == 404, f"{path} -> {resp.status_code}"

        posted = await client.post(
            f"/api/board/{lid}/posts", json={"body": BODY}, headers=stranger
        )
        assert posted.status_code == 404


class TestTeamClaims:
    async def test_co_owners_both_keep_their_team(
        self, client: AsyncClient, auth_headers, espn_league
    ):
        """Two managers of one team is normal, and used to erase the first one.

        `Team.owner_user_id` holds a single user, so the second claim unclaimed
        the first and their roster vanished from the app.
        """
        from app.services import mock_data

        lid = espn_league["league"]["id"]
        team_id = espn_league["teams"][0]["id"]
        other = await _second_user(client)
        await client.post(
            "/api/leagues/connect",
            json={"league_id": mock_data.MOCK_ESPN_LEAGUE_ID},
            headers=other,
        )

        for headers in (auth_headers, other):
            resp = await client.put(f"/api/teams/{team_id}/claim", headers=headers)
            assert resp.status_code == 200, resp.text

        # Each of them sees that team as theirs, and only that one.
        for headers in (auth_headers, other):
            me = await client.get("/api/auth/me", headers=headers)
            uid = me.json()["id"]
            teams = await client.get(f"/api/teams/league/{lid}", headers=headers)
            mine = [t["id"] for t in teams.json() if t["owner_user_id"] == uid]
            assert mine == [team_id]

    async def test_claiming_a_second_team_moves_the_claim(
        self, client: AsyncClient, auth_headers, espn_league
    ):
        lid = espn_league["league"]["id"]
        first, second = (t["id"] for t in espn_league["teams"][:2])

        assert (await client.put(f"/api/teams/{first}/claim", headers=auth_headers)).status_code == 200
        assert (await client.put(f"/api/teams/{second}/claim", headers=auth_headers)).status_code == 200

        me = await client.get("/api/auth/me", headers=auth_headers)
        uid = me.json()["id"]
        teams = await client.get(f"/api/teams/league/{lid}", headers=auth_headers)
        assert [t["id"] for t in teams.json() if t["owner_user_id"] == uid] == [second]


class TestCoOwnedTeam:
    """David and Jake co-own one ESPN team. Everything has to work for both.

    This is the shape the bug actually took in production, so it gets a test
    that walks the whole surface rather than just the claim endpoint.
    """

    async def _both_on_one_team(self, client: AsyncClient, auth_headers, espn_league):
        from app.services import mock_data

        lid = espn_league["league"]["id"]
        team_id = espn_league["teams"][0]["id"]
        other = await _second_user(client)
        await client.post(
            "/api/leagues/connect",
            json={"league_id": mock_data.MOCK_ESPN_LEAGUE_ID},
            headers=other,
        )
        for headers in (auth_headers, other):
            resp = await client.put(f"/api/teams/{team_id}/claim", headers=headers)
            assert resp.status_code == 200, resp.text
        return lid, team_id, other

    async def test_every_league_page_answers_for_both(
        self, client: AsyncClient, auth_headers, espn_league, mock_mode
    ):
        lid, team_id, other = await self._both_on_one_team(
            client, auth_headers, espn_league
        )

        # The pages that hang off "which team is mine".
        for headers, who in ((auth_headers, "owner"), (other, "co-owner")):
            for path in (
                f"/api/leagues/{lid}",
                f"/api/teams/league/{lid}",
                f"/api/teams/{team_id}/roster",
                f"/api/board/{lid}/posts",
                f"/api/leagues/{lid}/matchups",
                f"/api/actions/{lid}",
            ):
                resp = await client.get(path, headers=headers)
                assert resp.status_code == 200, f"{who} {path} -> {resp.status_code} {resp.text[:200]}"

    async def test_the_action_plan_is_about_their_shared_team(
        self, client: AsyncClient, auth_headers, espn_league, mock_mode
    ):
        lid, _, other = await self._both_on_one_team(client, auth_headers, espn_league)

        plans = [
            (await client.get(f"/api/actions/{lid}", headers=h)).json()
            for h in (auth_headers, other)
        ]
        assert plans[0]["team"] == plans[1]["team"]

    async def test_neither_is_offered_a_trade_with_themselves(
        self, client: AsyncClient, auth_headers, espn_league, mock_mode
    ):
        """The trade chip used to pick any team with no owner_user_id, which
        after a co-owned claim could be the asker's own team."""
        lid, _, other = await self._both_on_one_team(client, auth_headers, espn_league)

        for headers in (auth_headers, other):
            resp = await client.get(f"/api/assistant/{lid}/suggestions", headers=headers)
            assert resp.status_code == 200, resp.text
            plan = (await client.get(f"/api/actions/{lid}", headers=headers)).json()
            mine = plan["team"]
            trade_chips = [s for s in resp.json()["suggestions"] if "trade with" in s]
            assert not any(mine in chip for chip in trade_chips), trade_chips
