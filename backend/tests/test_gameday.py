"""
Game day: your players and your opponent's, mapped onto the live NFL slate.

The interesting logic is the ranking. A generic scoreboard sorts by kickoff
time; this has to sort by how much each game decides *this* matchup, which is
the only reason the view exists.
"""
import pytest

from app.api.gameday import _leverage, _summarize, _why_watch

pytestmark = pytest.mark.integration


def player(name="A Player", team="BUF", state="in", projected=10.0, points=0.0,
           injury=None):
    return {
        "player_id": 1, "name": name, "position": "WR", "slot": "WR",
        "team": team, "projected": projected, "points": points,
        "injury_status": injury, "game_state": state,
    }


class TestLeverage:
    """Sorting by kickoff time would bury the game that decides the week."""

    def test_a_game_with_both_sides_outranks_one_with_only_yours(self):
        game = {"state": "in"}
        both = _leverage(game, [player(projected=10)], [player(projected=10)])
        mine_only = _leverage(game, [player(projected=20)], [])
        assert both > mine_only

    def test_a_live_game_outranks_one_that_has_not_kicked_off(self):
        live = _leverage({"state": "in"}, [player(projected=10)], [])
        upcoming = _leverage({"state": "pre"}, [player(projected=10)], [])
        assert live > upcoming

    def test_an_upcoming_game_outranks_a_finished_one(self):
        upcoming = _leverage({"state": "pre"}, [player(projected=10)], [])
        final = _leverage({"state": "post"}, [player(projected=10)], [])
        assert upcoming > final

    def test_more_points_at_stake_ranks_higher(self):
        big = _leverage({"state": "in"}, [player(projected=25)], [])
        small = _leverage({"state": "in"}, [player(projected=4)], [])
        assert big > small

    def test_a_game_nobody_is_in_scores_zero(self):
        assert _leverage({"state": "in"}, [], []) == 0.0


class TestSummary:
    def test_counts_each_side_of_the_afternoon(self):
        summary = _summarize([
            player(state="in"), player(state="in"),
            player(state="pre"),
            player(state="post"),
        ])
        assert summary["playing_now"] == 2
        assert summary["yet_to_play"] == 1
        assert summary["finished"] == 1

    def test_points_in_play_covers_live_and_upcoming_but_not_finished(self):
        # The number that settles a Sunday argument: what is still to come.
        summary = _summarize([
            player(state="in", projected=12.0),
            player(state="pre", projected=8.0),
            player(state="post", projected=20.0),
        ])
        assert summary["points_in_play"] == 20.0
        assert summary["projected_total"] == 40.0

    def test_a_ruled_out_player_is_not_counted_as_still_to_come(self):
        # His points are gone, not pending; counting them inflates the outlook.
        summary = _summarize([player(state="pre", projected=15.0, injury="OUT")])
        assert summary["yet_to_play"] == 0
        assert summary["points_in_play"] == 0.0

    def test_a_questionable_player_still_counts(self):
        summary = _summarize([player(state="pre", projected=15.0, injury="QUESTIONABLE")])
        assert summary["yet_to_play"] == 1

    def test_a_player_with_no_game_counts_in_none_of_the_buckets(self):
        # A bye week or a free agent maps to no game at all.
        summary = _summarize([player(state=None, projected=9.0)])
        assert summary["playing_now"] == summary["yet_to_play"] == summary["finished"] == 0
        assert summary["points_in_play"] == 0.0

    def test_banked_points_are_reported_separately(self):
        summary = _summarize([player(state="post", points=18.4, projected=15.0)])
        assert summary["points"] == 18.4


class TestWhyWatch:
    def test_names_a_lone_player_on_each_side(self):
        why = _why_watch([player(name="Josh Allen")], [player(name="CeeDee Lamb")])
        assert "Josh Allen" in why and "CeeDee Lamb" in why

    def test_counts_them_once_there_are_several(self):
        why = _why_watch([player(), player(), player()], [])
        assert "3 starters" in why

    def test_says_nothing_when_neither_side_is_involved(self):
        assert _why_watch([], []) == ""


class TestEndpoint:
    async def test_needs_a_claimed_team(self, client, auth_headers, espn_league, mock_mode):
        lid = espn_league["league"]["id"]
        resp = await client.get(f"/api/gameday/{lid}", headers=auth_headers)
        assert resp.status_code == 400
        assert "Claim your team" in resp.json()["detail"]

    async def test_404_for_a_league_you_do_not_own(self, client, auth_headers):
        assert (await client.get("/api/gameday/9999", headers=auth_headers)).status_code == 404

    async def test_requires_auth(self, client, espn_league):
        lid = espn_league["league"]["id"]
        assert (await client.get(f"/api/gameday/{lid}")).status_code == 401

    @pytest.fixture
    async def gameday(self, client, auth_headers, espn_league, mock_mode):
        lid = espn_league["league"]["id"]
        team = espn_league["teams"][0]
        await client.put(f"/api/teams/{team['id']}/claim", headers=auth_headers)
        resp = await client.get(f"/api/gameday/{lid}", headers=auth_headers)
        assert resp.status_code == 200, resp.text
        return resp.json()

    async def test_reports_both_sides_of_the_matchup(self, gameday):
        assert gameday["my_team"]["name"]
        assert gameday["opponent"]["name"]
        assert gameday["my_team"]["name"] != gameday["opponent"]["name"]

    async def test_only_lists_starters(self, gameday, mock_mode):
        from app.services import mock_data
        roster = mock_data.espn_team_roster(1, None)["roster"]
        bench = {p["full_name"] for p in roster if not p.get("is_starter")}
        listed = {p["name"] for p in gameday["my_team"]["players"]}
        assert listed and not (listed & bench)

    async def test_every_game_listed_involves_somebody(self, gameday):
        # A card for a game neither side is in is noise on a Sunday.
        for game in gameday["games"]:
            assert game["mine"] or game["theirs"]

    async def test_games_are_ranked_by_leverage_not_kickoff(self, gameday):
        leverage = [g["leverage"] for g in gameday["games"]]
        assert leverage == sorted(leverage, reverse=True)

    async def test_each_game_explains_why_it_matters(self, gameday):
        for game in gameday["games"]:
            assert game["why"]

    async def test_players_carry_the_state_of_their_game(self, gameday):
        states = {p["game_state"] for p in gameday["my_team"]["players"]}
        assert states & {"in", "pre", "post"}

    async def test_a_player_is_attached_to_his_own_team_s_game(self, gameday):
        for game in gameday["games"]:
            sides = {game["home"]["abbr"], game["away"]["abbr"]}
            for p in game["mine"] + game["theirs"]:
                assert p["team"] in sides

    async def test_nobody_appears_in_two_games(self, gameday):
        seen = [p["name"] for g in gameday["games"] for p in g["mine"]]
        assert len(seen) == len(set(seen))

    async def test_the_summary_agrees_with_the_player_list(self, gameday):
        players = gameday["my_team"]["players"]
        summary = gameday["my_team"]["summary"]
        assert summary["playing_now"] == sum(1 for p in players if p["game_state"] == "in")
        assert summary["finished"] == sum(1 for p in players if p["game_state"] == "post")
