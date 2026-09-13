"""
ESPN and Sleeper must behave the same.

Everything downstream — the roster page, game day, the primer, the assistant's
context, the cross-league view — reads one normalized shape and does not care
which platform a league came from. A gap here does not fail loudly; it renders
an empty team or a zero score, which is how Sleeper leagues quietly stayed
half-broken.

These tests run the *same assertions* against both platforms rather than
testing each separately, so a shape that drifts on one side fails immediately.
"""
import pytest

from app.services.sleeper_sync import current_week, normalized_matchups, scoring_type_from

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
        "espn": {"league": espn_league["league"]["id"], "team": espn_league["teams"][0]["id"]},
        "sleeper": {"league": sleeper_id, "team": sleeper_teams[0]["id"]},
    }


PLATFORMS = ["espn", "sleeper"]


class TestScoringType:
    """Sleeper publishes points-per-reception, not a label."""

    def test_full_ppr(self):
        assert scoring_type_from({"rec": 1}) == "ppr"

    def test_half_ppr(self):
        assert scoring_type_from({"rec": 0.5}) == "half_ppr"

    def test_standard(self):
        assert scoring_type_from({"rec": 0}) == "standard"

    def test_missing_settings_are_standard(self):
        assert scoring_type_from(None) == "standard"
        assert scoring_type_from({}) == "standard"


class TestCurrentWeek:
    async def test_prefers_the_authoritative_nfl_state(self, mock_mode):
        from app.services.sleeper_service import SleeperService

        # The league claims week 1; the NFL state says otherwise and wins,
        # because a league's `leg` is frozen the moment it is read.
        week = await current_week(SleeperService(), {"settings": {"leg": 1}})
        assert week != 1

    async def test_falls_back_to_the_league_leg(self, mock_mode, monkeypatch):
        from app.services.sleeper_service import SleeperError, SleeperService

        async def unavailable():
            raise SleeperError("down")

        service = SleeperService()
        monkeypatch.setattr(service, "get_nfl_state", unavailable)
        assert await current_week(service, {"settings": {"leg": 7}}) == 7

    async def test_defaults_to_week_one_with_nothing_to_go_on(self, mock_mode, monkeypatch):
        from app.services.sleeper_service import SleeperError, SleeperService

        async def unavailable():
            raise SleeperError("down")

        service = SleeperService()
        monkeypatch.setattr(service, "get_nfl_state", unavailable)
        assert await current_week(service, {}) == 1


class TestEndpointParity:
    """The same request must succeed on both platforms."""

    @pytest.mark.parametrize("platform", PLATFORMS)
    async def test_league_detail(self, client, auth_headers, both, platform):
        lid = both[platform]["league"]
        resp = await client.get(f"/api/leagues/{lid}", headers=auth_headers)
        assert resp.status_code == 200, f"{platform}: {resp.text}"
        assert resp.json()["name"]

    @pytest.mark.parametrize("platform", PLATFORMS)
    async def test_sync(self, client, auth_headers, both, platform):
        """Sleeper leagues could not be re-synced at all before this."""
        lid = both[platform]["league"]
        resp = await client.post(f"/api/leagues/{lid}/sync", headers=auth_headers)
        assert resp.status_code == 200, f"{platform}: {resp.text}"
        assert resp.json()["success"] is True

    @pytest.mark.parametrize("platform", PLATFORMS)
    async def test_waiver_budgets(self, client, auth_headers, both, platform):
        lid = both[platform]["league"]
        resp = await client.get(f"/api/leagues/{lid}/waiver-budgets", headers=auth_headers)
        assert resp.status_code == 200, f"{platform}: {resp.text}"

        budgets = resp.json()
        assert budgets, f"{platform} reported no budgets"
        for budget in budgets:
            assert budget["team_name"]
            assert budget["total_budget"] > 0
            assert budget["current_budget"] + budget["spent_budget"] == pytest.approx(
                budget["total_budget"]
            )

    @pytest.mark.parametrize("platform", PLATFORMS)
    async def test_matchups(self, client, auth_headers, both, platform):
        lid = both[platform]["league"]
        resp = await client.get(f"/api/leagues/{lid}/matchups", headers=auth_headers)
        assert resp.status_code == 200, f"{platform}: {resp.text}"

    @pytest.mark.parametrize("platform", PLATFORMS)
    async def test_gameday(self, client, auth_headers, both, platform):
        lid = both[platform]["league"]
        resp = await client.get(f"/api/gameday/{lid}", headers=auth_headers)
        assert resp.status_code == 200, f"{platform}: {resp.text}"
        assert resp.json()["my_team"]["players"]

    @pytest.mark.parametrize("platform", PLATFORMS)
    async def test_primer(self, client, auth_headers, both, platform):
        lid = both[platform]["league"]
        resp = await client.get(f"/api/assistant/{lid}/primer", headers=auth_headers)
        assert resp.status_code == 200, f"{platform}: {resp.text}"
        assert resp.json()["projected"] > 0, f"{platform} projected nothing"

    @pytest.mark.parametrize("platform", PLATFORMS)
    async def test_narrative(self, client, auth_headers, both, platform):
        lid = both[platform]["league"]
        resp = await client.get(f"/api/content/{lid}/narrative/week/13", headers=auth_headers)
        assert resp.status_code == 200, f"{platform}: {resp.text}"


class TestRosterShapeParity:
    """The contract every downstream consumer reads."""

    CONTRACT = (
        "player_id", "full_name", "position_name", "lineup_slot_name",
        "is_starter", "on_injured_reserve",
        "projected_points", "applied_points", "pro_team_abbr",
    )

    @pytest.mark.parametrize("platform", PLATFORMS)
    async def test_roster_entries_carry_the_contract(
        self, client, auth_headers, both, platform
    ):
        team_id = both[platform]["team"]
        resp = await client.get(f"/api/teams/{team_id}/roster", headers=auth_headers)
        assert resp.status_code == 200, f"{platform}: {resp.text}"

        roster = resp.json()["roster"]
        assert roster, f"{platform} returned an empty roster"
        for player in roster:
            for field in self.CONTRACT:
                assert field in player, f"{platform} roster missing {field}"

    @pytest.mark.parametrize("platform", PLATFORMS)
    async def test_starters_are_a_subset_not_everyone(
        self, client, auth_headers, both, platform
    ):
        team_id = both[platform]["team"]
        roster = (
            await client.get(f"/api/teams/{team_id}/roster", headers=auth_headers)
        ).json()["roster"]

        starters = [p for p in roster if p["is_starter"]]
        assert starters, f"{platform} flagged nobody as starting"
        assert len(starters) < len(roster), f"{platform} flagged everybody as starting"

    @pytest.mark.parametrize("platform", PLATFORMS)
    async def test_points_are_populated(self, client, auth_headers, both, platform):
        """Zeroed points were the symptom that hid the Sleeper gap for weeks."""
        team_id = both[platform]["team"]
        roster = (
            await client.get(f"/api/teams/{team_id}/roster", headers=auth_headers)
        ).json()["roster"]

        assert sum(p["projected_points"] or 0 for p in roster) > 0, f"{platform} projected 0"

    @pytest.mark.parametrize("platform", PLATFORMS)
    async def test_players_carry_a_pro_team(self, client, auth_headers, both, platform):
        """Needed to map a player onto an NFL game, and for headshots."""
        team_id = both[platform]["team"]
        roster = (
            await client.get(f"/api/teams/{team_id}/roster", headers=auth_headers)
        ).json()["roster"]

        with_team = [p for p in roster if p["pro_team_abbr"]]
        assert len(with_team) > len(roster) / 2, f"{platform}: most players had no pro team"


class TestSleeperMatchupPairing:
    """Sleeper has no home and away: two rows sharing a matchup_id are the game."""

    async def test_rows_are_paired_into_games(self, mock_mode):
        from app.services import mock_data

        games = await normalized_matchups("mock_sleeper_league", mock_data.MOCK_CURRENT_WEEK)
        assert games
        for game in games:
            assert game["home_team_id"] is not None
            assert game["away_team_id"] is not None
            assert game["home_team_id"] != game["away_team_id"]

    async def test_nobody_appears_in_two_games(self, mock_mode):
        from app.services import mock_data

        games = await normalized_matchups("mock_sleeper_league", mock_data.MOCK_CURRENT_WEEK)
        rosters = [g["home_team_id"] for g in games] + [g["away_team_id"] for g in games]
        assert len(rosters) == len(set(rosters))

    async def test_pairing_is_stable_between_calls(self, mock_mode):
        """The lower roster id is home, so ordering does not flap."""
        from app.services import mock_data

        week = mock_data.MOCK_CURRENT_WEEK
        first = await normalized_matchups("mock_sleeper_league", week)
        second = await normalized_matchups("mock_sleeper_league", week)
        assert first == second

        for game in first:
            assert game["home_team_id"] < game["away_team_id"]

    async def test_a_winner_is_named_from_the_scores(self, mock_mode):
        from app.services import mock_data

        for game in await normalized_matchups("mock_sleeper_league", mock_data.MOCK_CURRENT_WEEK):
            if game["home_score"] > game["away_score"]:
                assert game["winner"] == "HOME"
            elif game["away_score"] > game["home_score"]:
                assert game["winner"] == "AWAY"


class TestSleeperLineupSlots:
    """A flex player must read FLEX, not whatever position he happens to play."""

    async def test_slots_follow_the_league_s_roster_positions(self, mock_mode):
        from app.services.sleeper_service import build_team_roster_entries

        roster = await build_team_roster_entries("mock_sleeper_league", 3, week=14)
        starters = [p for p in roster if p["is_starter"]]

        from app.services import mock_data
        expected = [
            slot for slot in mock_data.sleeper_league()["roster_positions"]
            if slot not in ("BN", "IR", "TAXI")
        ]
        assert [p["lineup_slot_name"] for p in starters] == expected[: len(starters)]

    async def test_bench_players_are_labelled_bench(self, mock_mode):
        from app.services.sleeper_service import build_team_roster_entries

        roster = await build_team_roster_entries("mock_sleeper_league", 3, week=14)
        for player in roster:
            if not player["is_starter"] and not player["on_injured_reserve"]:
                assert player["lineup_slot_name"] == "BENCH"
