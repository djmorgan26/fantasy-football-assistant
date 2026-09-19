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

        espn_team = espn_league["teams"][0]
        await client.put(f"/api/teams/{espn_team['id']}/claim", headers=auth_headers)

        # Claim the Sleeper roster that actually shares players with the ESPN
        # team. The two leagues draft from differently-rotated pools, so most
        # pairings overlap by nothing — and a fixture that picks one of those
        # tests the cross-platform join against an empty set.
        espn_names = {
            p["full_name"]
            for p in mock_data.espn_team_roster(espn_team["espn_team_id"], None)["roster"]
        }
        players_meta = mock_data.sleeper_all_players()
        overlap = {
            r["roster_id"]: len(espn_names & {
                players_meta[str(pid)]["full_name"]
                for pid in (r.get("players") or []) if str(pid) in players_meta
            })
            for r in mock_data.sleeper_rosters()
        }
        best_roster = max(overlap, key=overlap.get)
        assert overlap[best_roster] > 0, "mock leagues share no players at all"

        sleeper_teams = (
            await client.get(f"/api/teams/league/{sleeper_league_id}", headers=auth_headers)
        ).json()
        mine = next(t for t in sleeper_teams if t["sleeper_roster_id"] == best_roster)
        await client.put(f"/api/teams/{mine['id']}/claim", headers=auth_headers)

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


class TestCrossLeagueSlate:
    """Game Day, widened to every league at once.

    The single-league view already answers "who do I have on the field"; the
    point of this one is that on a Sunday you do not want to pick a league
    first. A player you start in one league and face in another is one row on
    one card, not two rows on two screens.
    """

    def holding(self, league_id=1, league="ESPN League", team="Mine",
                starting=True, projected=12.0, points=8.0, slot="WR"):
        return {
            "league_id": league_id, "league": league, "team": team,
            "starting": starting, "slot": slot,
            "projected": projected, "points": points,
        }

    def entry(self, name="Josh Allen", team="BUF", position="QB",
              for_rows=None, against_rows=None, injury=None):
        return {
            "name": name, "position": position, "team": team, "player_id": 1,
            "injury_status": injury,
            "for": [] if for_rows is None else for_rows,
            "against": [] if against_rows is None else against_rows,
        }

    def game(self, game_id="g1", state="in", home="MIA", away="BUF"):
        return {
            "id": game_id, "state": state, "detail": "Q4 2:41",
            "home": {"abbr": home, "name": home, "score": "17"},
            "away": {"abbr": away, "name": away, "score": "24"},
        }

    def slate(self, entries, games):
        from app.api.portfolio import _slate
        return _slate({str(i): e for i, e in enumerate(entries)}, games)

    def test_a_game_nobody_of_yours_is_in_gets_no_card(self):
        # The whole reason a generic scoreboard is useless on a Sunday.
        out = self.slate(
            [self.entry(team="BUF", for_rows=[self.holding()])],
            [self.game(away="BUF"), self.game("g2", home="DAL", away="PHI")],
        )
        assert [g["id"] for g in out] == ["g1"]

    def test_a_player_benched_everywhere_is_not_a_reason_to_watch(self):
        out = self.slate(
            [self.entry(for_rows=[self.holding(starting=False)])],
            [self.game()],
        )
        assert out == []

    def test_one_player_carries_every_league_he_is_in_it_for(self):
        out = self.slate(
            [self.entry(for_rows=[
                self.holding(league_id=1, league="ESPN League"),
                self.holding(league_id=2, league="Sleeper League"),
            ])],
            [self.game()],
        )
        leagues = [h["league"] for h in out[0]["players"][0]["for"]]
        assert leagues == ["ESPN League", "Sleeper League"]

    def test_rooting_for_and_against_the_same_man_is_one_row_not_two(self):
        out = self.slate(
            [self.entry(
                for_rows=[self.holding(league_id=1, league="ESPN League")],
                against_rows=[self.holding(league_id=2, league="Sleeper League",
                                           team="Pain Train")],
            )],
            [self.game()],
        )
        players = out[0]["players"]
        assert len(players) == 1
        assert players[0]["conflict"] is True
        assert out[0]["conflicts"] == 1

    def test_the_headline_number_is_the_biggest_stake_any_league_has(self):
        # Scoring settings differ per league, so there is no one true number.
        out = self.slate(
            [self.entry(for_rows=[
                self.holding(league_id=1, projected=12.0, points=8.0),
                self.holding(league_id=2, projected=18.0, points=14.0),
            ])],
            [self.game()],
        )
        player = out[0]["players"][0]
        assert player["projected"] == 18.0
        assert player["points"] == 14.0

    def test_conflicts_sort_above_everyone_else(self):
        out = self.slate(
            [
                self.entry(name="Big Plain", for_rows=[self.holding(projected=30.0)]),
                self.entry(name="Small Conflict",
                           for_rows=[self.holding(projected=4.0)],
                           against_rows=[self.holding(league_id=2, projected=4.0)]),
            ],
            [self.game()],
        )
        assert [p["name"] for p in out[0]["players"]] == ["Small Conflict", "Big Plain"]

    def test_a_contested_game_outranks_one_only_you_have_players_in(self):
        contested = self.slate(
            [self.entry(team="BUF", for_rows=[self.holding(projected=10.0)],
                        against_rows=[self.holding(league_id=2, projected=10.0)])],
            [self.game(away="BUF")],
        )
        mine_only = self.slate(
            [self.entry(team="BUF", for_rows=[self.holding(projected=20.0)])],
            [self.game(away="BUF")],
        )
        assert contested[0]["leverage"] > mine_only[0]["leverage"]

    def test_a_live_game_outranks_one_that_has_not_kicked_off(self):
        live = self.slate([self.entry(for_rows=[self.holding()])], [self.game(state="in")])
        pre = self.slate([self.entry(for_rows=[self.holding()])], [self.game(state="pre")])
        assert live[0]["leverage"] > pre[0]["leverage"]

    def test_games_come_back_ranked(self):
        out = self.slate(
            [
                self.entry(name="A", team="BUF", for_rows=[self.holding(projected=4.0)]),
                self.entry(name="B", team="DAL", for_rows=[self.holding(projected=40.0)]),
            ],
            [self.game("g1", away="BUF"), self.game("g2", home="DAL", away="PHI")],
        )
        assert [g["id"] for g in out] == ["g2", "g1"]
        assert [g["leverage"] for g in out] == sorted(
            (g["leverage"] for g in out), reverse=True
        )

    def test_each_card_says_why_it_is_worth_watching(self):
        out = self.slate(
            [self.entry(for_rows=[self.holding()],
                        against_rows=[self.holding(league_id=2)])],
            [self.game()],
        )
        why = out[0]["why"]
        assert "1 of yours" in why and "cutting both ways" in why


class TestLiveTotals:
    """The four numbers that say how your whole Sunday is going."""

    def totals(self, slate):
        from app.api.portfolio import _live_totals
        return _live_totals(slate)

    def card(self, state="in", players=None):
        return {"id": "g1", "state": state, "players": players or []}

    def player(self, for_rows=None, against_rows=None, injury=None):
        return {
            "name": "A Player", "injury_status": injury,
            "for": for_rows or [], "against": against_rows or [],
            "conflict": bool(for_rows and against_rows),
        }

    def holding(self, projected=10.0):
        return {"league_id": 1, "league": "L", "team": "T", "slot": "WR",
                "points": 0.0, "projected": projected}

    def test_counts_your_players_on_the_field_right_now(self):
        out = self.totals([self.card("in", [
            self.player(for_rows=[self.holding()]),
            self.player(for_rows=[self.holding()]),
        ])])
        assert out["playing_now"] == 2
        assert out["games"] == 1

    def test_counts_your_players_who_have_not_kicked_off(self):
        out = self.totals([self.card("pre", [self.player(for_rows=[self.holding()])])])
        assert out["yet_to_play"] == 1
        assert out["playing_now"] == 0

    def test_a_player_ruled_out_is_not_still_to_come(self):
        out = self.totals([
            self.card("pre", [self.player(for_rows=[self.holding()], injury="OUT")])
        ])
        assert out["yet_to_play"] == 0
        assert out["points_in_play"] == 0

    def test_points_still_in_play_count_every_league_he_starts_in(self):
        # He is one player, but two lineups are waiting on him.
        out = self.totals([self.card("in", [
            self.player(for_rows=[self.holding(projected=12.0),
                                  self.holding(projected=8.0)])
        ])])
        assert out["points_in_play"] == 20.0

    def test_points_already_banked_are_not_in_play(self):
        out = self.totals([self.card("post", [self.player(for_rows=[self.holding()])])])
        assert out["points_in_play"] == 0
        assert out["playing_now"] == 0

    def test_the_other_side_is_counted_separately(self):
        out = self.totals([self.card("in", [
            self.player(against_rows=[self.holding()])
        ])])
        assert out["theirs_playing_now"] == 1
        assert out["playing_now"] == 0


class TestPortfolioEndpoint:
    @pytest.fixture
    async def portfolio_of(self, client, auth_headers, espn_league, sleeper_league, mock_mode):
        for league in (espn_league, sleeper_league):
            team = league["teams"][0]
            await client.put(f"/api/teams/{team['id']}/claim", headers=auth_headers)
        resp = await client.get("/api/portfolio", headers=auth_headers)
        assert resp.status_code == 200, resp.text
        return resp.json()

    async def test_carries_the_live_slate(self, portfolio_of):
        assert "games" in portfolio_of
        assert "live" in portfolio_of
        assert portfolio_of["slate_size"] > 0

    async def test_every_game_listed_has_somebody_of_yours_in_it(self, portfolio_of):
        for game in portfolio_of["games"]:
            assert game["players"]
            assert game["yours"] or game["theirs"]

    async def test_games_are_ranked_by_leverage(self, portfolio_of):
        leverage = [g["leverage"] for g in portfolio_of["games"]]
        assert leverage == sorted(leverage, reverse=True)

    async def test_a_player_is_attached_to_his_own_team_s_game(self, portfolio_of):
        for game in portfolio_of["games"]:
            sides = {game["home"]["abbr"], game["away"]["abbr"]}
            for player in game["players"]:
                assert player["team"] in sides

    async def test_nobody_appears_in_two_games(self, portfolio_of):
        seen = [p["name"] for g in portfolio_of["games"] for p in g["players"]]
        assert len(seen) == len(set(seen))

    async def test_the_live_count_agrees_with_the_cards(self, portfolio_of):
        live = sum(1 for g in portfolio_of["games"] if g["state"] == "in")
        assert portfolio_of["live"]["games"] == live

    async def test_requires_auth(self, client):
        assert (await client.get("/api/portfolio")).status_code == 401
