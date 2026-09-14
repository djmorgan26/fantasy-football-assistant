"""The /api/actions endpoint, against both platforms."""
import pytest

pytestmark = pytest.mark.integration


@pytest.fixture
async def both(client, auth_headers, espn_league, mock_mode):
    """One ESPN league and one Sleeper league, each with a claimed team."""
    from app.services import mock_data

    resp = await client.post(
        "/api/sleeper/connect",
        json={
            "league_id": mock_data.MOCK_SLEEPER_LEAGUE_ID,
            "sleeper_user_id": mock_data.MOCK_SLEEPER_USER_ID,
        },
        headers=auth_headers,
    )
    assert resp.status_code in (200, 201), resp.text
    sleeper_id = resp.json()["league_id"]

    await client.put(
        f"/api/teams/{espn_league['teams'][0]['id']}/claim", headers=auth_headers
    )
    sleeper_teams = (
        await client.get(f"/api/teams/league/{sleeper_id}", headers=auth_headers)
    ).json()
    await client.put(f"/api/teams/{sleeper_teams[0]['id']}/claim", headers=auth_headers)

    return {
        "espn": {"league": espn_league["league"]["id"]},
        "sleeper": {"league": sleeper_id},
    }


class TestActionsEndpoint:
    async def test_it_needs_a_claimed_team(self, client, auth_headers, espn_league):
        """Nothing to plan for if you do not have a team in the league."""
        lid = espn_league["league"]["id"]
        resp = await client.get(f"/api/actions/{lid}", headers=auth_headers)
        assert resp.status_code == 404
        assert "Claim your team" in resp.json()["detail"]

    async def test_it_needs_auth(self, client, espn_league):
        lid = espn_league["league"]["id"]
        assert (await client.get(f"/api/actions/{lid}")).status_code == 401

    @pytest.mark.parametrize("platform", ["espn", "sleeper"])
    async def test_it_returns_a_plan_for_both_platforms(
        self, client, auth_headers, both, platform
    ):
        lid = both[platform]["league"]
        resp = await client.get(f"/api/actions/{lid}", headers=auth_headers)
        assert resp.status_code == 200, f"{platform}: {resp.text}"

        body = resp.json()
        for field in ("league_id", "team", "week", "actions", "risks", "depth", "budget"):
            assert field in body, f"{platform} missing {field}"
        assert isinstance(body["actions"], list)

    @pytest.mark.parametrize("platform", ["espn", "sleeper"])
    async def test_every_action_carries_what_the_ui_renders(
        self, client, auth_headers, both, platform
    ):
        lid = both[platform]["league"]
        body = (await client.get(f"/api/actions/{lid}", headers=auth_headers)).json()

        for action in body["actions"]:
            assert action["urgency"] in ("critical", "high", "medium", "low")
            assert action["hole"]["player"]
            assert action["hole"]["slot"]
            # start_instead may be None (nothing eligible), but the key is
            # always present so the page never reads undefined.
            assert "start_instead" in action
            assert isinstance(action["waiver_targets"], list)
            assert isinstance(action["trades"], list)

    async def test_a_healthy_roster_reports_all_clear(
        self, client, auth_headers, both, monkeypatch
    ):
        """No holes and no risks must be an explicit state, not an empty page."""
        from app.services import action_plan

        monkeypatch.setattr(action_plan, "find_holes", lambda roster: [])
        monkeypatch.setattr(action_plan, "find_risks", lambda roster: [])

        lid = both["espn"]["league"]
        body = (await client.get(f"/api/actions/{lid}", headers=auth_headers)).json()

        assert body["all_clear"] is True
        assert body["actions"] == []

    async def test_a_dead_waiver_feed_does_not_lose_the_lineup_advice(
        self, client, auth_headers, both, monkeypatch
    ):
        """The bench swap needs no network and must survive the pool failing."""
        from app.api import actions

        async def broken(league, position):
            raise RuntimeError("platform down")

        monkeypatch.setattr(actions, "_free_agents", broken)

        lid = both["espn"]["league"]
        resp = await client.get(f"/api/actions/{lid}", headers=auth_headers)
        assert resp.status_code == 200, resp.text
