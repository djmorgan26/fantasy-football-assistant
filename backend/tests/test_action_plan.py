"""The plan built for a roster with a hole in it.

Modelled on the real case this was written for: A.J. Brown on IR in a starting
WR slot, Jalen Coker on the bench off a good week.
"""
import pytest

from app.services import action_plan as ap

pytestmark = pytest.mark.integration


def player(name, pos, slot, *, starter, proj=0.0, last=0.0, status=None, ir=False):
    return {
        "full_name": name, "player_id": name.lower().replace(" ", "-"),
        "position_name": pos, "lineup_slot_name": slot,
        "is_starter": starter, "on_injured_reserve": ir,
        "projected_points": proj, "applied_points": last,
        "injury_status": status, "pro_team_abbr": "PHI",
    }


@pytest.fixture
def roster():
    return [
        player("Jalen Hurts", "QB", "QB", starter=True, proj=21.0),
        player("Saquon Barkley", "RB", "RB", starter=True, proj=18.0),
        player("Bijan Robinson", "RB", "RB", starter=True, proj=17.0),
        player("A.J. Brown", "WR", "WR", starter=True, proj=15.0,
               status="INJURY_RESERVE", ir=True),
        player("Puka Nacua", "WR", "WR", starter=True, proj=14.0),
        player("George Kittle", "TE", "TE", starter=True, proj=11.0),
        player("Cam Skattebo", "RB", "FLEX", starter=True, proj=9.0),
        # Bench
        player("Jalen Coker", "WR", "BENCH", starter=False, proj=10.5, last=33.8),
        player("Romeo Doubs", "WR", "BENCH", starter=False, proj=7.0, last=6.0),
        player("Tyjae Spears", "RB", "BENCH", starter=False, proj=6.0, last=4.0),
        player("Hurt Guy", "WR", "BENCH", starter=False, proj=12.0, status="OUT"),
    ]


class TestFindHoles:
    def test_an_ir_starter_is_a_hole(self, roster):
        holes = ap.find_holes(roster)
        assert [h["player"] for h in holes] == ["A.J. Brown"]
        assert holes[0]["slot"] == "WR"
        assert holes[0]["status"] == "INJURY_RESERVE"

    def test_a_healthy_roster_has_none(self, roster):
        healthy = [p for p in roster if p["full_name"] != "A.J. Brown"]
        assert ap.find_holes(healthy) == []

    def test_a_hurt_bench_player_is_not_a_hole(self, roster):
        """He is not in the lineup, so he costs nothing this week."""
        assert "Hurt Guy" not in [h["player"] for h in ap.find_holes(roster)]

    def test_an_out_starter_counts_even_without_the_ir_flag(self):
        out = [player("Someone", "WR", "WR", starter=True, proj=12.0, status="OUT")]
        assert len(ap.find_holes(out)) == 1

    def test_holes_are_ordered_by_what_they_cost(self):
        two = [
            player("Small", "WR", "WR", starter=True, proj=4.0, status="OUT"),
            player("Big", "RB", "RB", starter=True, proj=19.0, status="OUT"),
        ]
        assert [h["player"] for h in ap.find_holes(two)] == ["Big", "Small"]


class TestBenchOptions:
    def test_it_finds_the_replacement(self, roster):
        hole = ap.find_holes(roster)[0]
        best = ap.bench_options(hole, roster)[0]
        assert best["player"] == "Jalen Coker"

    def test_it_will_not_offer_an_injured_replacement(self, roster):
        """Swapping one zero for another is not a fix."""
        hole = ap.find_holes(roster)[0]
        assert "Hurt Guy" not in [o["player"] for o in ap.bench_options(hole, roster)]

    def test_it_respects_slot_eligibility(self, roster):
        """A WR cannot fill a QB slot, however well he projects."""
        hole = {"slot": "QB", "position": "QB"}
        assert ap.bench_options(hole, roster) == []

    def test_a_flex_hole_accepts_rb_wr_and_te(self, roster):
        hole = {"slot": "FLEX", "position": "RB"}
        positions = {o["position"] for o in ap.bench_options(hole, roster)}
        assert positions <= {"RB", "WR", "TE"} and positions


class TestEligibility:
    @pytest.mark.parametrize("slot,pos,ok", [
        ("FLEX", "RB", True), ("FLEX", "WR", True), ("FLEX", "TE", True),
        ("FLEX", "QB", False), ("FLEX", "K", False),
        ("SUPER_FLEX", "QB", True), ("WR", "WR", True), ("WR", "RB", False),
        ("D/ST", "DEF", True), ("RB/WR", "TE", False),
    ])
    def test_table(self, slot, pos, ok):
        assert ap.eligible_for(slot, pos) is ok

    def test_an_unknown_slot_demands_an_exact_match(self):
        """Guessing "yes" here would recommend an illegal lineup."""
        assert ap.eligible_for("MYSTERY", "WR") is False
        assert ap.eligible_for("MYSTERY", "MYSTERY") is True

    def test_missing_values_are_not_eligible(self):
        assert ap.eligible_for(None, "WR") is False
        assert ap.eligible_for("FLEX", None) is False


class TestUrgency:
    def test_no_eligible_bench_player_is_critical(self):
        hole = {"points_lost": 15.0}
        assert ap.urgency_for(hole, None) == "critical"

    def test_a_big_drop_is_high(self):
        assert ap.urgency_for({"points_lost": 20.0}, {"projected": 5.0}) == "high"

    def test_a_deep_bench_makes_a_star_injury_low(self):
        """It is the size of the drop that matters, not the name."""
        assert ap.urgency_for({"points_lost": 18.0}, {"projected": 17.0}) == "low"


class TestFaabAdvice:
    def test_it_bids_a_share_of_what_is_left(self):
        advice = ap.faab_advice(remaining=60, total=100, urgency="high")
        assert advice["suggested_bid"] == 12       # 20% of 60, not of 100
        assert advice["spent_pct"] == 40

    def test_urgency_moves_the_bid(self):
        critical = ap.faab_advice(100, 100, "critical")["suggested_bid"]
        low = ap.faab_advice(100, 100, "low")["suggested_bid"]
        assert critical > low

    def test_an_empty_budget_says_so(self):
        advice = ap.faab_advice(remaining=0, total=100, urgency="high")
        assert advice["suggested_bid"] == 0
        assert "free-agent claim" in advice["note"]

    def test_a_worthwhile_claim_never_bids_zero(self):
        assert ap.faab_advice(remaining=3, total=100, urgency="low")["suggested_bid"] >= 1

    def test_a_league_without_faab_gets_no_advice(self):
        assert ap.faab_advice(None, None, "high") is None
        assert ap.faab_advice(50, 0, "high") is None


class TestWaiverOptions:
    def test_it_only_offers_players_who_fit_the_slot(self, roster):
        hole = ap.find_holes(roster)[0]           # WR
        pool = [
            {"full_name": "Free WR", "position_name": "WR", "projected_points": 9},
            {"full_name": "Free QB", "position_name": "QB", "projected_points": 25},
        ]
        assert [o["player"] for o in ap.waiver_options(hole, pool)] == ["Free WR"]

    def test_it_flags_a_contested_add(self, roster):
        hole = ap.find_holes(roster)[0]
        pool = [{"full_name": "Hot Add", "position_name": "WR", "projected_points": 9}]
        out = ap.waiver_options(hole, pool, trending={"Hot Add": 4200})
        assert out[0]["contested"] is True and out[0]["added_by"] == 4200


class TestDepthAndTrades:
    def test_injured_players_do_not_count_as_depth(self, roster):
        """A roster that looks fine on paper while one injury guts it."""
        depth = ap.positional_depth(roster)
        assert "Hurt Guy" not in str(depth)
        assert depth["WR"]["count"] == 3   # Brown and Hurt Guy both excluded

    def test_it_finds_a_team_with_the_mirror_problem(self):
        """Deep at RB, thin at WR: the partner is whoever is the other way round."""
        mine = ap.positional_depth([
            player("RB1", "RB", "RB", starter=True, proj=15.0),
            player("RB2", "RB", "RB", starter=True, proj=12.0),
            player("RB3", "RB", "BENCH", starter=False, proj=9.0),
            player("RB4", "RB", "BENCH", starter=False, proj=8.0),
            player("WR1", "WR", "WR", starter=True, proj=13.0),
        ])
        assert mine["RB"]["count"] - mine["RB"]["starters"] >= 2   # the surplus

        rivals = [
            # Thin at RB (wants my surplus) and deep at WR (can pay for it).
            {"team": "Mirror", "depth": {"RB": {"count": 1, "starters": 1},
                                         "WR": {"count": 5, "starters": 2}}},
            # Deep everywhere: wants nothing I have spare.
            {"team": "Also Deep", "depth": {"RB": {"count": 5, "starters": 2},
                                            "WR": {"count": 5, "starters": 2}}},
        ]
        angles = ap.trade_angles(mine, rivals, need="WR")

        assert [a["team"] for a in angles] == ["Mirror"]
        assert angles[0]["they_need"] == "RB"
        assert angles[0]["they_can_spare"] == "WR"

    def test_no_surplus_means_no_trade_pitch(self):
        thin = ap.positional_depth([
            player("Only RB", "RB", "RB", starter=True, proj=10.0),
        ])
        assert ap.trade_angles(thin, [{"team": "X", "depth": {}}], need="WR") == []
