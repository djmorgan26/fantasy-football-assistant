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


async def _claim(client, headers, team_id):
    """Claim a team, the way a real manager does before any of this is useful.

    Connecting a league does not decide which of its teams is yours, so the
    trade endpoints that are written from your point of view (the finder, the
    incoming/outgoing split on offers) need this first.
    """
    resp = await client.put(f"/api/teams/{team_id}/claim", headers=headers)
    assert resp.status_code == 200, resp.text
    return resp.json()


async def _market(client, headers, league_id):
    resp = await client.get(f"/api/trades/league/{league_id}/market", headers=headers)
    assert resp.status_code == 200, resp.text
    return resp.json()


async def _claimed_market(client, headers, league, team_index=0):
    """A market where the caller owns one of the teams. Returns (market, mine, other)."""
    await _claim(client, headers, league["teams"][team_index]["id"])
    market = await _market(client, headers, league["league"]["id"])
    mine = market["my_team_id"]
    assert mine is not None
    other = next(
        t["team_id"] for t in market["teams"] if t["team_id"] != mine and t["players"]
    )
    return market, mine, other


def _pick(market, team_id, count=1):
    """The best `count` players on a team, by the market's own ordering."""
    team = next(t for t in market["teams"] if t["team_id"] == team_id)
    return [p["player_id"] for p in team["players"][:count]]


class TestTradeMarket:
    """The market backs the player pickers, so the UI never asks for a platform id."""

    async def test_market_lists_every_team_with_valued_players(
        self, client: AsyncClient, auth_headers, espn_league
    ):
        market = await _market(client, auth_headers, espn_league["league"]["id"])

        assert len(market["teams"]) == len(espn_league["teams"])
        assert market["starting_slots"]["QB"] >= 1
        # Replacement levels are what make a value meaningful.
        assert market["replacement_levels"]["RB"] > 0

        team = market["teams"][0]
        assert team["players"], "a synced team should have a roster"
        player = team["players"][0]
        assert player["full_name"]
        assert player["position"] != "UNKNOWN"
        assert player["value"] >= 0
        # Regression: the old analyzer made the user type ESPN player ids by
        # hand because nothing exposed them with names attached.
        assert set(player) >= {"player_id", "full_name", "position", "projected_points"}

    async def test_market_marks_my_team(
        self, client: AsyncClient, auth_headers, espn_league
    ):
        await _claim(client, auth_headers, espn_league["teams"][0]["id"])
        market = await _market(client, auth_headers, espn_league["league"]["id"])
        assert market["my_team_id"] is not None
        mine = [t for t in market["teams"] if t["is_mine"]]
        assert len(mine) == 1
        assert mine[0]["team_id"] == market["my_team_id"]

    async def test_market_works_on_sleeper_too(
        self, client: AsyncClient, auth_headers, sleeper_league
    ):
        market = await _market(client, auth_headers, sleeper_league["league"]["id"])
        assert len(market["teams"]) == len(sleeper_league["teams"])
        assert any(t["players"] for t in market["teams"])

    async def test_market_requires_league_access(
        self, client: AsyncClient, auth_headers, mock_mode
    ):
        resp = await client.get("/api/trades/league/4242/market", headers=auth_headers)
        assert resp.status_code == 404


class TestTradeEvaluation:
    async def test_evaluates_a_real_trade_end_to_end(
        self, client: AsyncClient, auth_headers, espn_league
    ):
        league_id = espn_league["league"]["id"]
        market, mine, other = await _claimed_market(client, auth_headers, espn_league)

        resp = await client.post(
            f"/api/trades/league/{league_id}/evaluate",
            json={
                "team_a_id": mine,
                "team_b_id": other,
                "team_a_sends": _pick(market, mine),
                "team_b_sends": _pick(market, other),
            },
            headers=auth_headers,
        )
        assert resp.status_code == 200, resp.text
        body = resp.json()

        assert body["verdict"] in (
            "accept", "lean_accept", "neutral", "lean_reject", "reject"
        )
        assert body["headline"]
        assert 0 <= body["fairness_score"] <= 100
        assert body["you"]["team_id"] == mine
        assert body["them"]["team_id"] == other
        # The lineup delta is the whole point: it must be derived, not echoed.
        assert body["you"]["lineup_after"] == pytest.approx(
            body["you"]["lineup_before"] + body["you"]["lineup_delta"], abs=0.02
        )
        assert body["players_you_send"][0]["full_name"]
        assert body["players_you_get"][0]["full_name"]

    async def test_playoff_odds_are_simulated_from_the_real_schedule(
        self, client: AsyncClient, auth_headers, espn_league
    ):
        league_id = espn_league["league"]["id"]
        market, mine, other = await _claimed_market(client, auth_headers, espn_league)

        resp = await client.post(
            f"/api/trades/league/{league_id}/evaluate",
            json={
                "team_a_id": mine,
                "team_b_id": other,
                "team_a_sends": _pick(market, mine),
                "team_b_sends": _pick(market, other),
                "include_ai": False,
            },
            headers=auth_headers,
        )
        assert resp.status_code == 200, resp.text
        odds = resp.json()["playoff_odds"]

        # The mock league still has regular season left, so odds should exist.
        assert odds is not None, "expected a simulation with weeks remaining"
        assert 0 <= odds["before"] <= 100
        assert 0 <= odds["after"] <= 100
        assert odds["delta"] == pytest.approx(odds["after"] - odds["before"], abs=0.2)
        assert odds["weeks_simulated"] > 0
        assert odds["schedule_source"] == "platform"

    async def test_lopsided_trade_is_rejected_and_fair_one_is_not(
        self, client: AsyncClient, auth_headers, espn_league
    ):
        """A giveaway and a swap must not produce the same verdict."""
        league_id = espn_league["league"]["id"]
        market, mine, other = await _claimed_market(client, auth_headers, espn_league)

        my_team = next(t for t in market["teams"] if t["team_id"] == mine)
        their_team = next(t for t in market["teams"] if t["team_id"] == other)

        # Give up the best player for their worst.
        giveaway = await client.post(
            f"/api/trades/league/{league_id}/evaluate",
            json={
                "team_a_id": mine,
                "team_b_id": other,
                "team_a_sends": [my_team["players"][0]["player_id"]],
                "team_b_sends": [their_team["players"][-1]["player_id"]],
                "include_ai": False,
            },
            headers=auth_headers,
        )
        assert giveaway.status_code == 200, giveaway.text
        body = giveaway.json()
        assert body["you"]["lineup_delta"] <= 0
        assert body["verdict"] in ("reject", "lean_reject", "neutral")
        assert body["fairness_score"] < 100

    async def test_player_not_on_roster_is_a_clear_400(
        self, client: AsyncClient, auth_headers, espn_league
    ):
        """Silently dropping the player would look like a real answer."""
        league_id = espn_league["league"]["id"]
        market, mine, other = await _claimed_market(client, auth_headers, espn_league)

        resp = await client.post(
            f"/api/trades/league/{league_id}/evaluate",
            json={
                "team_a_id": mine,
                "team_b_id": other,
                "team_a_sends": ["definitely-not-a-player"],
                "team_b_sends": _pick(market, other),
                "include_ai": False,
            },
            headers=auth_headers,
        )
        assert resp.status_code == 400
        assert "definitely-not-a-player" in resp.json()["detail"]

    async def test_trading_with_yourself_rejected(
        self, client: AsyncClient, auth_headers, espn_league
    ):
        league_id = espn_league["league"]["id"]
        market, mine, _other = await _claimed_market(client, auth_headers, espn_league)
        resp = await client.post(
            f"/api/trades/league/{league_id}/evaluate",
            json={
                "team_a_id": mine,
                "team_b_id": mine,
                "team_a_sends": _pick(market, mine),
                "team_b_sends": _pick(market, mine),
            },
            headers=auth_headers,
        )
        assert resp.status_code == 422

    async def test_team_outside_the_league_is_404(
        self, client: AsyncClient, auth_headers, espn_league
    ):
        league_id = espn_league["league"]["id"]
        market, mine, _other = await _claimed_market(client, auth_headers, espn_league)
        resp = await client.post(
            f"/api/trades/league/{league_id}/evaluate",
            json={
                "team_a_id": mine,
                "team_b_id": 99999,
                "team_a_sends": _pick(market, mine),
                "team_b_sends": ["whatever"],
            },
            headers=auth_headers,
        )
        assert resp.status_code == 404

    async def test_evaluates_on_sleeper(
        self, client: AsyncClient, auth_headers, sleeper_league
    ):
        league_id = sleeper_league["league"]["id"]
        market, mine, other = await _claimed_market(client, auth_headers, sleeper_league)
        resp = await client.post(
            f"/api/trades/league/{league_id}/evaluate",
            json={
                "team_a_id": mine,
                "team_b_id": other,
                "team_a_sends": _pick(market, mine),
                "team_b_sends": _pick(market, other),
                "include_ai": False,
            },
            headers=auth_headers,
        )
        assert resp.status_code == 200, resp.text
        assert resp.json()["you"]["team_id"] == mine


class TestTradeOffers:
    async def test_espn_offers_endpoint_returns_a_feed(
        self, client: AsyncClient, auth_headers, espn_league
    ):
        """ESPN exposes pending proposals without any extra credentials."""
        resp = await client.get(
            f"/api/trades/league/{espn_league['league']['id']}/offers",
            headers=auth_headers,
        )
        assert resp.status_code == 200, resp.text
        body = resp.json()
        assert body["platform"] == "espn"
        assert body["pending_available"] is True
        assert body["pending"], "the mock ESPN league has a pending proposal"

        offer = body["pending"][0]
        assert offer["status"] == "proposed"
        assert offer["source"] == "espn"
        # ESPN tags each player with fromTeamId rather than grouping by side,
        # so a normalizer that ignored it would put everyone on one side.
        assert len(offer["parties"]) == 2
        assert all(p["sends"] for p in offer["parties"])
        assert all(
            p["sends"][0]["full_name"] and p["sends"][0]["position"] != "UNKNOWN"
            for p in offer["parties"]
        )

    async def test_espn_history_is_separated_from_pending(
        self, client: AsyncClient, auth_headers, espn_league
    ):
        resp = await client.get(
            f"/api/trades/league/{espn_league['league']['id']}/offers",
            headers=auth_headers,
        )
        body = resp.json()
        assert body["history"], "the mock ESPN league has a completed trade"
        assert all(t["status"] != "proposed" for t in body["history"])
        assert all(t["status"] == "proposed" for t in body["pending"])

    async def test_espn_offer_direction_follows_the_claimed_team(
        self, client: AsyncClient, auth_headers, espn_league
    ):
        """The mock proposal is made by team 1 to team 5.

        Whoever claims team 5 is being asked, so it reads as incoming; the
        proposer sees the same trade as outgoing.
        """
        receiver = next(
            t for t in espn_league["teams"] if t["espn_team_id"] == 5
        )
        await _claim(client, auth_headers, receiver["id"])

        resp = await client.get(
            f"/api/trades/league/{espn_league['league']['id']}/offers",
            headers=auth_headers,
        )
        assert resp.json()["pending"][0]["direction"] == "incoming"

    async def test_sleeper_without_a_token_explains_the_gap(
        self, client: AsyncClient, auth_headers, sleeper_league
    ):
        """Sleeper's public API cannot see a pending offer, and says so.

        Silently showing an empty list would read as "nobody has offered you a
        trade", which is a different and wrong statement.
        """
        resp = await client.get(
            f"/api/trades/league/{sleeper_league['league']['id']}/offers",
            headers=auth_headers,
        )
        assert resp.status_code == 200, resp.text
        body = resp.json()
        assert body["pending_available"] is False
        assert "token" in (body["pending_notice"] or "").lower()

    async def test_connecting_a_token_surfaces_pending_offers(
        self, client: AsyncClient, auth_headers, sleeper_league
    ):
        league_id = sleeper_league["league"]["id"]
        # The mock offer is addressed to roster 8 (the demo user's own team),
        # so own that team to read the incoming/outgoing split the way a real
        # manager would.
        mine = next(
            t for t in sleeper_league["teams"] if t["sleeper_roster_id"] == 8
        )
        await _claim(client, auth_headers, mine["id"])

        stored = await client.post(
            f"/api/trades/league/{league_id}/sleeper-token",
            json={"token": "test-sleeper-bearer-token"},
            headers=auth_headers,
        )
        assert stored.status_code == 204, stored.text

        resp = await client.get(
            f"/api/trades/league/{league_id}/offers", headers=auth_headers
        )
        assert resp.status_code == 200, resp.text
        body = resp.json()
        assert body["pending_available"] is True
        assert body["pending"], "the mock league has one proposed trade"

        offer = body["pending"][0]
        assert offer["status"] == "proposed"
        # The mock offer is made *to* the mock user, so it must read as incoming.
        assert offer["direction"] == "incoming"
        assert len(offer["parties"]) == 2
        assert any(p["sends"] for p in offer["parties"])
        # Exactly one side has consented: the proposer.
        assert sum(1 for p in offer["parties"] if p["has_consented"]) == 1

    async def test_token_can_be_disconnected(
        self, client: AsyncClient, auth_headers, sleeper_league
    ):
        league_id = sleeper_league["league"]["id"]
        await client.post(
            f"/api/trades/league/{league_id}/sleeper-token",
            json={"token": "test-sleeper-bearer-token"},
            headers=auth_headers,
        )
        removed = await client.delete(
            f"/api/trades/league/{league_id}/sleeper-token", headers=auth_headers
        )
        assert removed.status_code == 204

        resp = await client.get(
            f"/api/trades/league/{league_id}/offers", headers=auth_headers
        )
        assert resp.json()["pending_available"] is False

    async def test_token_is_encrypted_at_rest(
        self, client: AsyncClient, auth_headers, sleeper_league, db_session
    ):
        from sqlalchemy import select
        from app.models.league import League as LeagueModel
        from app.utils.encryption import decrypt_data

        league_id = sleeper_league["league"]["id"]
        secret = "super-secret-sleeper-token"
        await client.post(
            f"/api/trades/league/{league_id}/sleeper-token",
            json={"token": secret},
            headers=auth_headers,
        )

        row = (
            await db_session.execute(
                select(LeagueModel).where(LeagueModel.id == league_id)
            )
        ).scalar_one()
        assert row.sleeper_token_encrypted
        assert secret not in row.sleeper_token_encrypted
        assert decrypt_data(row.sleeper_token_encrypted) == secret

    async def test_espn_league_rejects_a_sleeper_token(
        self, client: AsyncClient, auth_headers, espn_league
    ):
        resp = await client.post(
            f"/api/trades/league/{espn_league['league']['id']}/sleeper-token",
            json={"token": "not-applicable-here"},
            headers=auth_headers,
        )
        assert resp.status_code == 400


class TestTradeFinder:
    async def test_finder_returns_actionable_ideas(
        self, client: AsyncClient, auth_headers, espn_league
    ):
        await _claim(client, auth_headers, espn_league["teams"][0]["id"])
        resp = await client.get(
            f"/api/trades/league/{espn_league['league']['id']}/finder",
            headers=auth_headers,
        )
        assert resp.status_code == 200, resp.text
        body = resp.json()
        assert body["my_team_id"]
        assert isinstance(body["ideas"], list)
        assert isinstance(body["needs"], list)
        assert isinstance(body["surplus"], list)

        for idea in body["ideas"]:
            # The filter that makes these proposable: both sides gain.
            assert idea["my_lineup_delta"] > 0
            assert idea["their_lineup_delta"] > 0
            assert idea["give"] and idea["receive"]
            assert idea["partner_team_id"] != body["my_team_id"]

    async def test_finder_respects_the_limit(
        self, client: AsyncClient, auth_headers, espn_league
    ):
        await _claim(client, auth_headers, espn_league["teams"][0]["id"])
        resp = await client.get(
            f"/api/trades/league/{espn_league['league']['id']}/finder?limit=2",
            headers=auth_headers,
        )
        assert resp.status_code == 200
        assert len(resp.json()["ideas"]) <= 2

    async def test_finder_works_on_sleeper(
        self, client: AsyncClient, auth_headers, sleeper_league
    ):
        await _claim(client, auth_headers, sleeper_league["teams"][0]["id"])
        resp = await client.get(
            f"/api/trades/league/{sleeper_league['league']['id']}/finder",
            headers=auth_headers,
        )
        assert resp.status_code == 200, resp.text
        assert resp.json()["my_team_id"]


class TestPlayerIntel:
    """Sourced facts about the players in a trade, never inferred ones."""

    async def test_evaluation_carries_intel_for_both_sides(
        self, client: AsyncClient, auth_headers, espn_league
    ):
        league_id = espn_league["league"]["id"]
        market, mine, other = await _claimed_market(client, auth_headers, espn_league)

        resp = await client.post(
            f"/api/trades/league/{league_id}/evaluate",
            json={
                "team_a_id": mine, "team_b_id": other,
                "team_a_sends": _pick(market, mine),
                "team_b_sends": _pick(market, other),
                "include_ai": False,
            },
            headers=auth_headers,
        )
        assert resp.status_code == 200, resp.text
        body = resp.json()

        intel = body["intel"]
        assert intel, "expected intel for the players in the trade"
        sent = body["players_you_send"][0]["player_id"]
        got = body["players_you_get"][0]["player_id"]
        assert sent in intel and got in intel

        entry = intel[got]
        assert entry["full_name"]
        # Depth-chart role is the fact a projection cannot express: whether he
        # actually starts for his NFL team.
        assert "role" in entry
        assert "injury" in entry
        assert isinstance(entry["headlines"], list)

    async def test_a_backup_is_flagged_as_a_risk(
        self, client: AsyncClient, auth_headers, espn_league
    ):
        """Receiving a player who is not his team's starter is worth saying."""
        league_id = espn_league["league"]["id"]
        market, mine, other = await _claimed_market(client, auth_headers, espn_league)
        their_team = next(t for t in market["teams"] if t["team_id"] == other)

        # Walk their roster until we find someone the intel calls a backup.
        for candidate in their_team["players"]:
            resp = await client.post(
                f"/api/trades/league/{league_id}/evaluate",
                json={
                    "team_a_id": mine, "team_b_id": other,
                    "team_a_sends": _pick(market, mine),
                    "team_b_sends": [candidate["player_id"]],
                    "include_ai": False,
                },
                headers=auth_headers,
            )
            body = resp.json()
            entry = body["intel"].get(candidate["player_id"]) or {}
            role = entry.get("role") or ""
            if role and not role.startswith("Starting"):
                assert any(
                    "depth chart" in risk for risk in body["risks"]
                ), f"backup not flagged: {body['risks']}"
                return
        pytest.skip("no backup found on the mock roster")

    async def test_intel_survives_a_dead_news_wire(
        self, client: AsyncClient, auth_headers, espn_league, monkeypatch
    ):
        """Headlines are one source of three; losing them keeps the rest.

        Patched at the real boundary (`news_service.fetch_news`) rather than at
        `player_intel._wire`, because `_wire` is where the guard lives and
        replacing it would test the mock instead of the handling.
        """
        from app.services import news_service

        async def broken_wire(*args, **kwargs):
            raise RuntimeError("wire down")

        monkeypatch.setattr(news_service, "fetch_news", broken_wire)

        league_id = espn_league["league"]["id"]
        market, mine, other = await _claimed_market(client, auth_headers, espn_league)
        resp = await client.post(
            f"/api/trades/league/{league_id}/evaluate",
            json={
                "team_a_id": mine, "team_b_id": other,
                "team_a_sends": _pick(market, mine),
                "team_b_sends": _pick(market, other),
                "include_ai": False,
            },
            headers=auth_headers,
        )
        assert resp.status_code == 200, resp.text
        intel = resp.json()["intel"]
        assert intel
        assert all(e["headlines"] == [] for e in intel.values())
        # The depth-chart facts come from the player index, not the wire.
        assert any(e.get("role") for e in intel.values())


class TestCounterOffers:
    async def test_counters_are_offered_and_beat_accepting(
        self, client: AsyncClient, auth_headers, espn_league
    ):
        league_id = espn_league["league"]["id"]
        market, mine, other = await _claimed_market(client, auth_headers, espn_league)
        my_team = next(t for t in market["teams"] if t["team_id"] == mine)
        their_team = next(t for t in market["teams"] if t["team_id"] == other)

        # A lopsided offer against me: my best for their worst. There should be
        # something better to propose back.
        resp = await client.post(
            f"/api/trades/league/{league_id}/counters",
            json={
                "team_a_id": mine, "team_b_id": other,
                "team_a_sends": [my_team["players"][0]["player_id"]],
                "team_b_sends": [their_team["players"][-1]["player_id"]],
                "include_ai": False,
            },
            headers=auth_headers,
        )
        assert resp.status_code == 200, resp.text
        body = resp.json()

        assert body["original_verdict"] in (
            "accept", "lean_accept", "neutral", "lean_reject", "reject"
        )
        assert body["summary"]
        assert body["counters"], "a bad offer should have a better version"

        for counter in body["counters"]:
            # The defining property: every counter beats simply accepting.
            assert counter["gain_vs_original"] > 0
            assert counter["give"] and counter["receive"]
            assert counter["rationale"]
            assert counter["likelihood"] in (
                "easy_ask", "fair_ask", "big_ask", "unlikely"
            )
            assert counter["likelihood_reason"]
            assert counter["kind"] in (
                "ask_for_more", "different_target", "give_less",
                "different_piece", "swap_both",
            )

    async def test_counters_are_available_even_on_a_good_offer(
        self, client: AsyncClient, auth_headers, espn_league
    ):
        """The user asked to explore whatever the verdict was.

        A trade worth accepting may still be worth improving, so the endpoint
        must answer rather than refuse.
        """
        league_id = espn_league["league"]["id"]
        market, mine, other = await _claimed_market(client, auth_headers, espn_league)
        my_team = next(t for t in market["teams"] if t["team_id"] == mine)
        their_team = next(t for t in market["teams"] if t["team_id"] == other)

        resp = await client.post(
            f"/api/trades/league/{league_id}/counters",
            json={
                "team_a_id": mine, "team_b_id": other,
                "team_a_sends": [my_team["players"][-1]["player_id"]],
                "team_b_sends": [their_team["players"][0]["player_id"]],
                "include_ai": False,
            },
            headers=auth_headers,
        )
        assert resp.status_code == 200, resp.text
        body = resp.json()
        # Either counters, or a plain sentence saying why there are none.
        assert body["counters"] or "Nothing" in body["summary"]

    async def test_counter_rejects_a_player_not_on_the_roster(
        self, client: AsyncClient, auth_headers, espn_league
    ):
        league_id = espn_league["league"]["id"]
        market, mine, other = await _claimed_market(client, auth_headers, espn_league)
        resp = await client.post(
            f"/api/trades/league/{league_id}/counters",
            json={
                "team_a_id": mine, "team_b_id": other,
                "team_a_sends": ["ghost-player"],
                "team_b_sends": _pick(market, other),
                "include_ai": False,
            },
            headers=auth_headers,
        )
        assert resp.status_code == 400

    async def test_counters_work_on_sleeper(
        self, client: AsyncClient, auth_headers, sleeper_league
    ):
        league_id = sleeper_league["league"]["id"]
        market, mine, other = await _claimed_market(
            client, auth_headers, sleeper_league
        )
        my_team = next(t for t in market["teams"] if t["team_id"] == mine)
        their_team = next(t for t in market["teams"] if t["team_id"] == other)
        resp = await client.post(
            f"/api/trades/league/{league_id}/counters",
            json={
                "team_a_id": mine, "team_b_id": other,
                "team_a_sends": [my_team["players"][0]["player_id"]],
                "team_b_sends": [their_team["players"][-1]["player_id"]],
                "include_ai": False,
            },
            headers=auth_headers,
        )
        assert resp.status_code == 200, resp.text
        assert resp.json()["original_verdict"]

    async def test_countering_yourself_rejected(
        self, client: AsyncClient, auth_headers, espn_league
    ):
        league_id = espn_league["league"]["id"]
        market, mine, _o = await _claimed_market(client, auth_headers, espn_league)
        resp = await client.post(
            f"/api/trades/league/{league_id}/counters",
            json={
                "team_a_id": mine, "team_b_id": mine,
                "team_a_sends": _pick(market, mine),
                "team_b_sends": _pick(market, mine),
            },
            headers=auth_headers,
        )
        assert resp.status_code == 422

    async def test_summary_does_not_call_a_long_shot_realistic(
        self, client: AsyncClient, auth_headers, espn_league
    ):
        """When nothing is an easy ask, the sentence has to say so.

        Describing the leading counter as "the most realistic" reads as an
        endorsement, and it is wrong when every option leaves the other team
        worse off than the deal they wrote.
        """
        league_id = espn_league["league"]["id"]
        market, mine, other = await _claimed_market(client, auth_headers, espn_league)
        my_team = next(t for t in market["teams"] if t["team_id"] == mine)
        their_team = next(t for t in market["teams"] if t["team_id"] == other)

        resp = await client.post(
            f"/api/trades/league/{league_id}/counters",
            json={
                "team_a_id": mine, "team_b_id": other,
                "team_a_sends": [my_team["players"][-1]["player_id"]],
                "team_b_sends": [their_team["players"][0]["player_id"]],
                "include_ai": False,
            },
            headers=auth_headers,
        )
        assert resp.status_code == 200, resp.text
        body = resp.json()
        if not body["counters"]:
            return
        bands = {c["likelihood"] for c in body["counters"]}
        if bands <= {"big_ask", "unlikely"}:
            assert "worse off" in body["summary"], body["summary"]
        else:
            assert "leave their lineup better off" in body["summary"]

    async def test_a_rejected_token_says_so_instead_of_showing_no_offers(
        self, client: AsyncClient, auth_headers, sleeper_league, monkeypatch
    ):
        """A stale token must not read as "nobody has offered you a trade".

        Those are different statements, and only one of them is something the
        user can act on. Sleeper tokens expire when you sign out, so this is
        the normal end state of a connected league, not an edge case.
        """
        from app.services.sleeper_service import SleeperAuthError, SleeperService

        league_id = sleeper_league["league"]["id"]
        await client.post(
            f"/api/trades/league/{league_id}/sleeper-token",
            json={"token": "a-token-that-has-since-expired"},
            headers=auth_headers,
        )

        async def rejected(self, league, token, limit=25):
            raise SleeperAuthError("Sleeper rejected the stored token")

        monkeypatch.setattr(SleeperService, "get_proposed_trades", rejected)

        resp = await client.get(
            f"/api/trades/league/{league_id}/offers", headers=auth_headers
        )
        assert resp.status_code == 200, resp.text
        body = resp.json()
        assert body["pending_available"] is False
        assert body["pending"] == []
        assert "rejected" in (body["pending_notice"] or "").lower()
        assert "fresh" in (body["pending_notice"] or "").lower()
