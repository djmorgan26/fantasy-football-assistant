"""
The cross-league view, and the Sleeper roster contract it depends on.

The headline case — owning a player in one league while playing against him in
another — only exists once rosters from both platforms come back in the same
shape. Sleeper's did not, which is why these live in the same file.
"""
import pytest

from app.api.portfolio import verdict

pytestmark = pytest.mark.integration


class TestVerdict:
    """Only starters count; a bench player is doing nothing to anybody."""

    def test_owning_him_everywhere(self):
        assert verdict(2, 0) == "rooting for him"

    def test_facing_him_everywhere(self):
        assert verdict(0, 2) == "rooting against him"

    def test_one_each_way_is_the_confusing_case(self):
        assert verdict(1, 1) == "a genuine wash"

    def test_an_even_split_at_any_size_is_still_a_wash(self):
        assert verdict(3, 3) == "a genuine wash"

    def test_a_lean_is_named_as_a_lean(self):
        assert verdict(2, 1) == "net rooting for him"
        assert verdict(1, 2) == "net rooting against him"


class TestSleeperRosterContract:
    """Sleeper rosters must come back in the shape everything downstream reads.

    They used to arrive as bare id arrays with no starter flag and no points,
    which did not fail loudly — it rendered Sleeper leagues as teams with nobody
    on them, everywhere except the roster page.
    """

    async def test_entries_carry_the_full_contract(self, mock_mode):
        from app.services.sleeper_service import build_team_roster_entries

        roster = await build_team_roster_entries("mock_sleeper_league", 3, week=14)
        assert roster

        for player in roster:
            for field in (
                "full_name", "position_name", "lineup_slot_name",
                "is_starter", "on_injured_reserve",
                "projected_points", "applied_points", "pro_team_abbr",
            ):
                assert field in player, f"{field} missing — downstream reads it"

    async def test_starters_are_flagged(self, mock_mode):
        from app.services.sleeper_service import build_team_roster_entries

        roster = await build_team_roster_entries("mock_sleeper_league", 3, week=14)
        starters = [p for p in roster if p["is_starter"]]
        assert starters, "a Sleeper team with no starters is the old bug"
        assert len(starters) < len(roster), "everyone cannot be starting"

    async def test_points_come_back_for_the_week(self, mock_mode):
        from app.services.sleeper_service import build_team_roster_entries

        roster = await build_team_roster_entries("mock_sleeper_league", 3, week=14)
        assert sum(p["applied_points"] for p in roster) > 0
        assert sum(p["projected_points"] for p in roster) > 0

    async def test_a_sleeper_roster_survives_a_missing_week(self, mock_mode):
        """Without a week there are no points yet, but the shape holds."""
        from app.services.sleeper_service import build_team_roster_entries

        roster = await build_team_roster_entries("mock_sleeper_league", 3)
        assert roster
        assert all("is_starter" in p for p in roster)


class TestPortfolio:
    @pytest.fixture
    async def two_leagues(self, client, auth_headers, espn_league, mock_mode):
        """Connect a Sleeper league alongside the ESPN one and claim a team in each."""
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
        sleeper_league_id = resp.json()["league_id"]

        await client.put(
            f"/api/teams/{espn_league['teams'][0]['id']}/claim", headers=auth_headers
        )
        sleeper_teams = (
            await client.get(f"/api/teams/league/{sleeper_league_id}", headers=auth_headers)
        ).json()
        await client.put(f"/api/teams/{sleeper_teams[0]['id']}/claim", headers=auth_headers)

        return {"espn": espn_league["league"]["id"], "sleeper": sleeper_league_id}

    async def test_requires_auth(self, client):
        assert (await client.get("/api/portfolio")).status_code == 401

    async def test_empty_for_someone_with_no_leagues(self, client, auth_headers):
        body = (await client.get("/api/portfolio", headers=auth_headers)).json()
        assert body["leagues"] == 0
        assert body["teams"] == 0
        assert body["weeks"] == body["conflicts"] == body["exposure"] == []

    async def test_reports_leagues_with_no_claimed_team(
        self, client, auth_headers, espn_league, mock_mode
    ):
        """A league missing from the view needs a reason, not silence."""
        body = (await client.get("/api/portfolio", headers=auth_headers)).json()
        assert body["leagues"] == 1
        assert body["teams"] == 0
        assert [u["name"] for u in body["unclaimed"]] == [espn_league["league"]["name"]]

    async def test_covers_both_platforms(self, client, auth_headers, two_leagues):
        body = (await client.get("/api/portfolio", headers=auth_headers)).json()
        assert body["teams"] == 2
        assert {w["platform"] for w in body["weeks"]} == {"espn", "sleeper"}

    async def test_a_sleeper_week_is_not_empty(self, client, auth_headers, two_leagues):
        """The regression that started this: Sleeper weeks scored zero."""
        body = (await client.get("/api/portfolio", headers=auth_headers)).json()
        sleeper = next(w for w in body["weeks"] if w["platform"] == "sleeper")

        assert sleeper["opponent"], "Sleeper pairs by matchup_id, not home/away"
        assert sleeper["projected"] > 0
        assert sleeper["points"] > 0

    async def test_weeks_are_ordered_most_precarious_first(
        self, client, auth_headers, two_leagues
    ):
        body = (await client.get("/api/portfolio", headers=auth_headers)).json()
        margins = [w["margin"] for w in body["weeks"]]
        assert margins == sorted(margins)

    async def test_a_week_is_labelled_by_how_safe_it_is(
        self, client, auth_headers, two_leagues
    ):
        body = (await client.get("/api/portfolio", headers=auth_headers)).json()
        for week in body["weeks"]:
            assert week["status"] in ("comfortable", "tight", "behind")
            if week["margin"] >= 15:
                assert week["status"] == "comfortable"

    async def test_players_are_matched_across_platforms_by_name(
        self, client, auth_headers, two_leagues
    ):
        """ESPN and Sleeper number the same human differently.

        An id-based join would find nothing between an ESPN league and a
        Sleeper one — which is exactly the pairing this page is for.
        """
        body = (await client.get("/api/portfolio", headers=auth_headers)).json()
        crossings = body["conflicts"] + body["exposure"]
        assert crossings, "no player matched across the two platforms"

    async def test_exposure_only_counts_players_in_more_than_one_league(
        self, client, auth_headers, two_leagues
    ):
        body = (await client.get("/api/portfolio", headers=auth_headers)).json()
        for entry in body["exposure"]:
            assert entry["leagues"] >= 2
            assert len(entry["for"]) >= 2
            # "A bad Sunday hurts more than once" is only true if he plays.
            assert entry["starting_in"] >= 1

    async def test_a_conflict_has_him_starting_on_both_sides(
        self, client, auth_headers, two_leagues
    ):
        body = (await client.get("/api/portfolio", headers=auth_headers)).json()
        for entry in body["conflicts"]:
            assert any(e["starting"] for e in entry["for"])
            assert any(e["starting"] for e in entry["against"])
            assert entry["verdict"]

    async def test_totals_agree_with_the_weeks(self, client, auth_headers, two_leagues):
        body = (await client.get("/api/portfolio", headers=auth_headers)).json()
        assert body["totals"]["points"] == pytest.approx(
            sum(w["points"] for w in body["weeks"]), abs=0.2
        )
        assert body["totals"]["winning"] == sum(1 for w in body["weeks"] if w["margin"] > 0)
