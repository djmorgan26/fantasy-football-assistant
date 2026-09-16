"""The trade maths, tested without a database, a league, or a network.

`trade_engine` is deliberately pure so that the parts a wrong answer would be
most embarrassing in (lineup optimisation, replacement level, playoff odds)
can be pinned to hand-checkable cases.
"""
import pytest

from app.services import trade_engine as te

pytestmark = pytest.mark.unit


def player(name, position, points, **extra):
    return {
        "player_id": name.lower().replace(" ", "_"),
        "full_name": name,
        "position_name": position,
        "projected_points": points,
        **extra,
    }


STANDARD = te.LineupSlots({"QB": 1, "RB": 2, "WR": 2, "TE": 1}, flex=1)


class TestPositions:
    @pytest.mark.parametrize(
        "raw,expected",
        [("D/ST", "DEF"), ("DST", "DEF"), ("PK", "K"), ("rb", "RB"), (None, "UNKNOWN")],
    )
    def test_normalizes_platform_spellings(self, raw, expected):
        assert te.normalize_position(raw) == expected

    def test_espn_numeric_lineup_slots(self):
        """ESPN keys lineupSlotCounts by slot id, which is not a position name."""
        slots = te.lineup_slots_from_settings(
            {"lineup_slots": {"0": 1, "2": 2, "4": 2, "6": 1, "23": 1, "20": 6}}
        )
        assert slots.counts["QB"] == 1
        assert slots.counts["RB"] == 2
        assert slots.flex == 1
        # Bench is not a starting slot and must not inflate the lineup.
        assert slots.total_starters == 7

    def test_sleeper_roster_positions(self):
        slots = te.lineup_slots_from_settings(
            None, ["QB", "RB", "RB", "WR", "WR", "TE", "FLEX", "BN", "BN"]
        )
        assert slots.counts["RB"] == 2
        assert slots.flex == 1
        assert slots.total_starters == 7

    def test_superflex_is_kept_separate_from_flex(self):
        slots = te.lineup_slots_from_settings(None, ["QB", "RB", "WR", "SUPER_FLEX"])
        assert slots.superflex == 1
        assert slots.flex == 0

    def test_unknown_settings_fall_back_rather_than_failing(self):
        slots = te.lineup_slots_from_settings(None, None)
        assert slots.counts == te.DEFAULT_SLOT_COUNTS
        assert slots.flex == te.DEFAULT_FLEX


class TestOptimalLineup:
    def test_picks_the_best_legal_lineup(self):
        roster = [
            player("QB1", "QB", 20), player("QB2", "QB", 18),
            player("RB1", "RB", 15), player("RB2", "RB", 12), player("RB3", "RB", 10),
            player("WR1", "WR", 14), player("WR2", "WR", 11),
            player("TE1", "TE", 8),
        ]
        total, chosen = te.optimal_lineup(roster, STANDARD)
        # QB1 + RB1 + RB2 + WR1 + WR2 + TE1 + RB3 in the flex.
        assert total == pytest.approx(20 + 15 + 12 + 14 + 11 + 8 + 10)
        assert len(chosen) == 7
        # The second QB cannot start in a league with no superflex.
        assert "QB2" not in [c["full_name"] for c in chosen]

    def test_flex_takes_the_best_remaining_eligible_player(self):
        """Dedicated slots are filled first, and the flex gets what is left.

        WR3 outscores WR2, so WR3 takes the second WR slot and WR2 drops to the
        flex. The flex is the leftovers, not a third pick of the whole pool.
        """
        roster = [
            player("QB1", "QB", 20),
            player("RB1", "RB", 15), player("RB2", "RB", 12),
            player("WR1", "WR", 14), player("WR2", "WR", 11), player("WR3", "WR", 13),
            player("TE1", "TE", 8),
        ]
        _, chosen = te.optimal_lineup(roster, STANDARD)
        by_name = {c["full_name"]: c["filled_slot"] for c in chosen}
        assert by_name["WR3"] == "WR"
        assert by_name["WR2"] == "FLEX"

    def test_flex_takes_the_highest_leftover_whatever_position_it_is(self):
        """Named by value so the expected answer is readable off the roster.

        RB15/RB13 fill the two RB slots and WR14/WR11 the two WR slots, leaving
        RB12 and WR4. The flex takes RB12: position is irrelevant once a player
        is eligible.
        """
        roster = [
            player("QB20", "QB", 20),
            player("RB15", "RB", 15), player("RB13", "RB", 13), player("RB12", "RB", 12),
            player("WR14", "WR", 14), player("WR11", "WR", 11), player("WR4", "WR", 4),
            player("TE8", "TE", 8),
        ]
        _, chosen = te.optimal_lineup(roster, STANDARD)
        flex = next(c for c in chosen if c["filled_slot"] == "FLEX")
        assert flex["full_name"] == "RB12"

    def test_injured_reserve_players_cannot_start(self):
        """An IR player counted as a starter silently inflates every lineup."""
        roster = [
            player("RB1", "RB", 25, on_injured_reserve=True),
            player("RB2", "RB", 10),
        ]
        total, chosen = te.optimal_lineup(roster, te.LineupSlots({"RB": 1}, flex=0))
        assert total == 10
        assert chosen[0]["full_name"] == "RB2"

    def test_short_roster_does_not_crash(self):
        total, chosen = te.optimal_lineup([player("RB1", "RB", 10)], STANDARD)
        assert total == 10
        assert len(chosen) == 1

    def test_superflex_can_start_a_second_quarterback(self):
        roster = [player("QB1", "QB", 22), player("QB2", "QB", 19), player("RB1", "RB", 9)]
        slots = te.LineupSlots({"QB": 1}, flex=0, superflex=1)
        total, chosen = te.optimal_lineup(roster, slots)
        assert total == pytest.approx(41)
        assert {c["full_name"] for c in chosen} == {"QB1", "QB2"}


class TestReplacementLevel:
    def test_baseline_is_the_last_startable_player(self):
        # 2 teams, 1 RB slot each, no flex: the 2nd best RB is replacement.
        pool = [player(f"RB{i}", "RB", 20 - i) for i in range(6)]
        levels = te.replacement_levels(pool, te.LineupSlots({"RB": 1}, flex=0), team_count=2)
        assert levels["RB"] == 19  # RB0=20, RB1=19

    def test_scarcity_makes_the_same_projection_worth_more_at_a_thin_position(self):
        pool = (
            [player(f"WR{i}", "WR", 20 - i * 0.2) for i in range(40)]
            + [player(f"TE{i}", "TE", 20 - i * 3.0) for i in range(12)]
        )
        slots = te.LineupSlots({"WR": 2, "TE": 1}, flex=0)
        levels = te.replacement_levels(pool, slots, team_count=10)

        same = player("Guy", "WR", 14)
        same_te = player("Guy", "TE", 14)
        # A steep positional dropoff means 14 points is worth far more at TE.
        assert te.value_over_replacement(same_te, levels) > te.value_over_replacement(same, levels)

    def test_below_replacement_is_worth_zero_not_negative(self):
        levels = {"RB": 12.0}
        assert te.value_over_replacement(player("Scrub", "RB", 3), levels) == 0.0

    def test_empty_pool_does_not_divide_by_zero(self):
        assert te.replacement_levels([], STANDARD, team_count=10)["RB"] == 0.0


class TestEvaluateSide:
    def test_upgrade_raises_the_lineup(self):
        roster = [player("RB1", "RB", 8), player("WR1", "WR", 10)]
        impact = te.evaluate_side(
            team_id=1, team_name="Mine", roster=roster,
            outgoing_ids=["rb1"], incoming=[player("RB Star", "RB", 18)],
            slots=te.LineupSlots({"RB": 1, "WR": 1}, flex=0),
            levels={"RB": 5.0, "WR": 5.0},
        )
        assert impact.lineup_delta == 10.0
        assert impact.value_delta == 10.0

    def test_surplus_at_a_full_position_adds_nothing_to_the_lineup(self):
        """The trap a raw points comparison falls into.

        Trading a startable WR for a better RB is a downgrade when both RB slots
        are already filled by better players: the incoming player rides the
        bench and the outgoing one was starting.
        """
        roster = [
            player("RB1", "RB", 20), player("RB2", "RB", 18),
            player("WR1", "WR", 12),
        ]
        slots = te.LineupSlots({"RB": 2, "WR": 1}, flex=0)
        impact = te.evaluate_side(
            team_id=1, team_name="Mine", roster=roster,
            outgoing_ids=["wr1"], incoming=[player("RB3", "RB", 15)],
            slots=slots, levels={"RB": 8.0, "WR": 8.0},
        )
        # Raw points say +3. The lineup says otherwise: WR1 was starting, RB3 is not.
        assert impact.lineup_delta == -12.0

    def test_depth_is_recomputed_after_the_trade(self):
        roster = [player("RB1", "RB", 20), player("RB2", "RB", 18)]
        impact = te.evaluate_side(
            team_id=1, team_name="Mine", roster=roster,
            outgoing_ids=["rb2"], incoming=[player("TE1", "TE", 14)],
            slots=te.LineupSlots({"RB": 2, "TE": 1}, flex=0),
            levels={"RB": 8.0, "TE": 6.0},
        )
        assert impact.depth_before["RB"]["startable"] == 2
        assert impact.depth_after["RB"]["startable"] == 1
        assert impact.depth_after["RB"]["surplus"] == -1
        assert impact.depth_after["TE"]["startable"] == 1


class TestFairness:
    def _side(self, value_in):
        return te.SideImpact(
            team_id=1, team_name="t", lineup_before=0, lineup_after=0,
            value_out=0, value_in=value_in, depth_before={}, depth_after={},
        )

    def test_even_value_scores_one_hundred(self):
        assert te.fairness_score(self._side(10), self._side(10)) == 100.0

    def test_totally_lopsided_scores_zero(self):
        assert te.fairness_score(self._side(20), self._side(0)) == 0.0

    def test_fairness_is_relative_to_trade_size(self):
        """A 2-point gap is lopsided in a small trade and trivial in a big one."""
        small = te.fairness_score(self._side(6), self._side(4))
        large = te.fairness_score(self._side(31), self._side(29))
        assert small < large

    def test_valueless_trade_is_neutral_rather_than_a_divide_by_zero(self):
        assert te.fairness_score(self._side(0), self._side(0)) == 50.0


class TestSimulation:
    def _teams(self, means):
        return [
            te.SimTeam(team_id=i, name=f"T{i}", wins=0, losses=0, points_for=0, weekly_mean=m)
            for i, m in enumerate(means)
        ]

    def _round_robin(self, n_teams, weeks):
        return [[(i, (i + 1) % n_teams) for i in range(0, n_teams, 2)] for _ in range(weeks)]

    def test_stronger_teams_make_the_playoffs_more_often(self):
        teams = self._teams([140, 130, 120, 110])
        odds = te.simulate_season(teams, self._round_robin(4, 8), playoff_spots=2, seed=7)
        assert odds[0] > odds[3]

    def test_probabilities_are_percentages(self):
        teams = self._teams([120, 120, 120, 120])
        odds = te.simulate_season(teams, self._round_robin(4, 6), playoff_spots=2, seed=7)
        for value in odds.values():
            assert 0.0 <= value <= 100.0

    def test_same_seed_gives_the_same_answer(self):
        """The odds *delta* is only meaningful if the noise cancels."""
        teams = self._teams([130, 120, 115, 110])
        schedule = self._round_robin(4, 8)
        first = te.simulate_season(teams, schedule, playoff_spots=2, seed=42)
        second = te.simulate_season(teams, schedule, playoff_spots=2, seed=42)
        assert first == second

    def test_a_better_lineup_raises_the_odds(self):
        schedule = self._round_robin(4, 10)
        before = te.simulate_season(self._teams([110, 125, 125, 125]), schedule, 2, seed=3)
        after = te.simulate_season(self._teams([135, 125, 125, 125]), schedule, 2, seed=3)
        assert after[0] > before[0]

    def test_no_schedule_left_still_returns_odds(self):
        odds = te.simulate_season(self._teams([120, 110]), [], playoff_spots=1, seed=1)
        assert set(odds) == {0, 1}

    def test_no_teams_is_empty_not_an_error(self):
        assert te.simulate_season([], [], playoff_spots=2) == {}


class TestOpportunityFinder:
    def test_finds_the_mirrored_surplus_trade(self):
        """Two teams with opposite holes should be matched.

        Mine is three deep at RB and has no startable TE; theirs is the reverse.
        The swap raises both starting lineups, which is the only kind of trade
        that gets accepted.
        """
        slots = te.LineupSlots({"RB": 1, "TE": 1}, flex=0)
        levels = {"RB": 8.0, "TE": 6.0, "QB": 0.0, "WR": 0.0, "K": 0.0, "DEF": 0.0}

        mine = [
            player("My RB1", "RB", 18), player("My RB2", "RB", 15),
            player("My TE1", "TE", 2),
        ]
        theirs = [
            player("Their TE1", "TE", 14), player("Their TE2", "TE", 12),
            player("Their RB1", "RB", 3),
        ]

        ideas = te.find_opportunities(
            my_team_id=1, my_roster=mine,
            other_rosters={2: theirs}, team_names={1: "Mine", 2: "Theirs"},
            slots=slots, levels=levels,
        )
        assert ideas, "expected a mutually beneficial swap"
        best = ideas[0]
        assert best.my_lineup_delta > 0
        assert best.their_lineup_delta > 0
        assert best.receive[0]["position_name"] == "TE"
        assert best.give[0]["position_name"] == "RB"

    def test_rejects_trades_the_other_side_would_never_accept(self):
        slots = te.LineupSlots({"RB": 1}, flex=0)
        levels = {"RB": 5.0}
        mine = [player("Bad RB", "RB", 6)]
        theirs = [player("Great RB", "RB", 25)]

        ideas = te.find_opportunities(
            my_team_id=1, my_roster=mine, other_rosters={2: theirs},
            team_names={1: "Mine", 2: "Theirs"}, slots=slots, levels=levels,
        )
        assert ideas == []

    def test_does_not_propose_trading_with_yourself(self):
        roster = [player("RB1", "RB", 10), player("TE1", "TE", 2)]
        ideas = te.find_opportunities(
            my_team_id=1, my_roster=roster, other_rosters={1: roster},
            team_names={1: "Mine"}, slots=STANDARD, levels={"RB": 5.0, "TE": 5.0},
        )
        assert ideas == []

    def test_respects_the_limit(self):
        slots = te.LineupSlots({"RB": 1, "WR": 1, "TE": 1}, flex=1)
        levels = {p: 4.0 for p in te.POSITIONS}
        mine = [player(f"M{i}", "RB", 20 - i) for i in range(6)] + [player("MTE", "TE", 1)]
        others = {
            tid: [player(f"T{tid}_{i}", "TE", 18 - i) for i in range(4)]
            for tid in (2, 3, 4)
        }
        ideas = te.find_opportunities(
            my_team_id=1, my_roster=mine, other_rosters=others,
            team_names={i: f"T{i}" for i in range(1, 5)},
            slots=slots, levels=levels, limit=3,
        )
        assert len(ideas) <= 3


class TestVerdict:
    def test_playoff_odds_outrank_weekly_points(self):
        """A trade can cost points a week and still be right, and vice versa."""
        verdict, reason = te.verdict_label(lineup_delta=-2.0, odds_delta=8.0, fairness=70)
        assert verdict == "accept"
        assert "playoff odds" in reason

    def test_falls_back_to_lineup_delta_without_odds(self):
        verdict, reason = te.verdict_label(lineup_delta=5.0, odds_delta=None, fairness=70)
        assert verdict == "accept"
        assert "starting lineup" in reason

    def test_a_wash_reads_as_neutral(self):
        verdict, _ = te.verdict_label(lineup_delta=0.1, odds_delta=0.2, fairness=95)
        assert verdict == "neutral"

    def test_a_bad_trade_is_rejected(self):
        verdict, _ = te.verdict_label(lineup_delta=-6.0, odds_delta=-9.0, fairness=20)
        assert verdict == "reject"
