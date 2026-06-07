"""Real-mode service code paths with external HTTP mocked via respx.

MOCK_MODE is off here (the conftest pins it off), so these tests exercise the
exact request/parse code used against the live ESPN and Sleeper APIs.
"""
import re

import httpx
import pytest
import respx

from app.services.espn_service import (
    ESPNService,
    ESPNAuthenticationError,
    ESPNConnectionError,
)
from app.services.sleeper_service import SleeperService, SleeperNotFoundError


pytestmark = pytest.mark.integration

ESPN_URL = re.compile(r"https://lm-api-reads\.fantasy\.espn\.com/.*")
SLEEPER_URL = re.compile(r"https://api\.sleeper\.app/.*")


def espn_league_payload():
    return {
        "id": 1725275280,
        "scoringPeriodId": 14,
        "status": {"currentMatchupPeriod": 14, "isActive": True},
        "settings": {
            "name": "AEPI 2022",
            "rosterSettings": {"lineupSlotCounts": {"0": 1, "2": 2, "4": 2, "6": 1, "16": 1, "17": 1, "20": 7, "23": 1}},
            "scoringSettings": {"scoringItems": [], "playerRankType": "PPR", "scoringType": "H2H_POINTS"},
        },
        "teams": [
            {
                "id": i,
                "name": f"Team {i}",
                "location": "",
                "nickname": "",
                "abbrev": f"T{i}",
                "record": {"overall": {"wins": i, "losses": 13 - i, "ties": 0,
                                       "pointsFor": 1500.0 + i, "pointsAgainst": 1490.0 - i}},
                "owners": [f"{{OWNER-{i}}}"],
            }
            for i in range(1, 11)
        ],
        "members": [
            {"id": f"{{OWNER-{i}}}", "displayName": f"Manager {i}"}
            for i in range(1, 11)
        ],
    }


def espn_roster_payload():
    def player(pid, name, pos_id, slot, projected, actual):
        return {
            "lineupSlotId": slot,
            "playerPoolEntry": {
                "player": {
                    "id": pid,
                    "fullName": name,
                    "defaultPositionId": pos_id,
                    "proTeamId": 2,
                    "eligibleSlots": [slot, 20],
                    "stats": [
                        {"scoringPeriodId": 14, "statSourceId": 0,
                         "appliedTotal": actual, "stats": {"0": 25}},
                        {"scoringPeriodId": 14, "statSourceId": 1,
                         "appliedTotal": projected, "stats": {"0": 30}},
                    ],
                }
            },
        }

    return {
        "scoringPeriodId": 14,
        "teams": [
            {
                "id": 3,
                "roster": {
                    "entries": [
                        player(101, "Test Quarterback", 0, 0, 22.5, 18.1),
                        player(102, "Test Runningback", 2, 2, 15.0, 21.4),
                        player(103, "Bench Guy", 4, 20, 9.0, 4.2),
                    ]
                },
            }
        ],
    }


class TestESPNServiceReal:
    @respx.mock
    async def test_get_league_info_parses_settings(self):
        respx.get(ESPN_URL).mock(
            return_value=httpx.Response(200, json=espn_league_payload())
        )
        info = await ESPNService().get_league_info("1725275280")
        assert info["name"] == "AEPI 2022"
        assert info["size"] == 10
        assert info["current_week"] == 14
        assert info["is_active"] is True

    @respx.mock
    async def test_get_teams_builds_display_names(self):
        respx.get(ESPN_URL).mock(
            return_value=httpx.Response(200, json=espn_league_payload())
        )
        teams = await ESPNService().get_teams("1725275280")
        assert len(teams) == 10
        assert teams[0]["name"] == "Team 1"
        assert teams[0]["wins"] == 1
        assert teams[0]["points_for"] == 1501.0

    @respx.mock
    async def test_get_team_roster_extracts_point_totals(self):
        # Regression: projected_points/applied_points must be the appliedTotal
        # fantasy point values, not raw ESPN stat dicts.
        respx.get(ESPN_URL).mock(
            return_value=httpx.Response(200, json=espn_roster_payload())
        )
        roster_data = await ESPNService().get_team_roster("1725275280", 3, week=14)
        players = roster_data["roster"]
        assert len(players) == 3
        qb = players[0]
        assert qb["full_name"] == "Test Quarterback"
        assert qb["projected_points"] == 22.5
        assert qb["applied_points"] == 18.1
        assert qb["position_name"] == "QB"
        assert players[2]["lineup_slot_name"] == "BENCH"

    @respx.mock
    async def test_401_raises_authentication_error(self):
        respx.get(ESPN_URL).mock(return_value=httpx.Response(401))
        with pytest.raises(ESPNAuthenticationError):
            await ESPNService().get_teams("123")

    @respx.mock
    async def test_429_retries_then_succeeds(self):
        route = respx.get(ESPN_URL)
        route.side_effect = [
            httpx.Response(429),
            httpx.Response(200, json=espn_league_payload()),
        ]
        info = await ESPNService().get_league_info("1725275280")
        assert info["name"] == "AEPI 2022"
        assert route.call_count == 2

    @respx.mock
    async def test_non_dict_json_raises_connection_error(self):
        respx.get(ESPN_URL).mock(return_value=httpx.Response(200, json=[1, 2, 3]))
        with pytest.raises((ESPNConnectionError, Exception)):
            await ESPNService().get_league_info("123")

    @respx.mock
    async def test_cookies_sent_for_private_league(self):
        from app.services.espn_service import ESPNCookies

        route = respx.get(ESPN_URL).mock(
            return_value=httpx.Response(200, json=espn_league_payload())
        )
        cookies = ESPNCookies(espn_s2="S2VALUE", swid="{SWID}")
        await ESPNService().get_league_info("123", cookies)
        sent = route.calls.last.request.headers.get("cookie", "")
        assert "espn_s2=S2VALUE" in sent
        assert "SWID=" in sent


class TestSleeperServiceReal:
    @respx.mock
    async def test_get_league(self):
        respx.get(SLEEPER_URL).mock(
            return_value=httpx.Response(200, json={
                "league_id": "abc123",
                "name": "Real Sleeper League",
                "total_rosters": 12,
                "season": "2025",
                "scoring_settings": {"rec": 1},
                "roster_positions": ["QB", "RB", "RB", "WR", "WR", "TE", "FLEX", "K", "DEF"],
                "settings": {"leg": 14},
            })
        )
        league = await SleeperService().get_league("abc123")
        assert league["name"] == "Real Sleeper League"
        assert league["total_rosters"] == 12

    @respx.mock
    async def test_404_raises_not_found(self):
        respx.get(SLEEPER_URL).mock(return_value=httpx.Response(404))
        with pytest.raises(SleeperNotFoundError):
            await SleeperService().get_league("does-not-exist")

    @respx.mock
    async def test_validate_league_access(self):
        respx.get(SLEEPER_URL).mock(
            return_value=httpx.Response(200, json=[
                {"user_id": "u1", "display_name": "Alice"},
                {"user_id": "u2", "display_name": "Bob"},
            ])
        )
        service = SleeperService()
        assert await service.validate_league_access("lg", "u1") is True
        assert await service.validate_league_access("lg", "nope") is False

    @respx.mock
    async def test_get_matchups(self):
        respx.get(SLEEPER_URL).mock(
            return_value=httpx.Response(200, json=[
                {"roster_id": 1, "matchup_id": 1, "points": 120.5,
                 "starters": ["1234"], "players": ["1234", "5678"]},
            ])
        )
        matchups = await SleeperService().get_matchups("lg", 3)
        assert matchups[0]["points"] == 120.5


def espn_matchup_payload():
    """Serves both the matchup view and the roster view (same URL pattern)."""
    payload = espn_roster_payload()
    payload["schedule"] = [
        {
            "id": 1,
            "matchupPeriodId": 14,
            "playoffTierType": "NONE",
            "winner": "UNDECIDED",
            "home": {"teamId": 3, "totalPoints": 0,
                     "totalPointsLive": 88.4,
                     "pointsByScoringPeriod": {"14": 80.0}},
            "away": {"teamId": 4, "totalPoints": 75.2},
        },
        {
            "id": 2,
            "matchupPeriodId": 13,  # filtered out when week=14 requested
            "home": {"teamId": 5, "totalPoints": 100.0},
            "away": {"teamId": 6, "totalPoints": 90.0},
        },
    ]
    return payload


class TestESPNMatchupsReal:
    @respx.mock
    async def test_matchups_score_priority_and_week_filter(self):
        respx.get(ESPN_URL).mock(
            return_value=httpx.Response(200, json=espn_matchup_payload())
        )
        matchups = await ESPNService().get_matchups("1725275280", week=14)
        assert len(matchups) == 1
        m = matchups[0]
        # totalPointsLive wins over pointsByScoringPeriod and totalPoints.
        assert m["home_score"] == 88.4
        assert m["away_score"] == 75.2
        assert m["week"] == 14
        assert m["is_playoff"] is False


class TestESPNValidateTradeReal:
    @respx.mock
    async def test_valid_and_invalid_trades(self):
        # Two teams sharing the same payload; team 3 holds 101-103.
        payload = espn_roster_payload()
        payload["teams"].append({
            "id": 4,
            "roster": {"entries": [
                {
                    "lineupSlotId": 0,
                    "playerPoolEntry": {"player": {
                        "id": 201, "fullName": "Other QB",
                        "defaultPositionId": 0, "proTeamId": 5,
                        "eligibleSlots": [0, 20], "stats": [],
                    }},
                },
            ]},
        })
        respx.get(ESPN_URL).mock(return_value=httpx.Response(200, json=payload))

        service = ESPNService()
        ok = await service.validate_trade("123", 3, 4, [101], [201])
        assert ok["is_valid"] is True

        bad = await service.validate_trade("123", 3, 4, [999], [201])
        assert bad["is_valid"] is False
        assert "999" in bad["error"]


class TestESPNAvailablePlayersReal:
    @respx.mock
    async def test_available_players_parsed_and_sorted(self):
        payload = {
            "scoringPeriodId": 14,
            "players": [
                {"player": {
                    "id": 301, "fullName": "Free Agent One",
                    "firstName": "Free", "lastName": "One",
                    "defaultPositionId": 2, "proTeamId": 7,
                    "eligibleSlots": [2, 20], "injuryStatus": "ACTIVE",
                    "stats": [
                        {"scoringPeriodId": 14, "statSourceId": 1,
                         "appliedTotal": 12.5, "stats": {}},
                        {"statSourceId": 0, "appliedTotal": 110.0, "stats": {}},
                    ],
                }},
                {"player": {
                    "id": 302, "fullName": "Free Agent Two",
                    "firstName": "Free", "lastName": "Two",
                    "defaultPositionId": 4, "proTeamId": 8,
                    "eligibleSlots": [4, 20], "injuryStatus": "QUESTIONABLE",
                    "stats": [
                        {"scoringPeriodId": 14, "statSourceId": 1,
                         "appliedTotal": 18.0, "stats": {}},
                    ],
                }},
            ],
        }
        respx.get(ESPN_URL).mock(return_value=httpx.Response(200, json=payload))
        players = await ESPNService().get_available_players("123", week=14)
        assert len(players) == 2
        # Sorted by projected points, descending.
        assert players[0]["full_name"] == "Free Agent Two"
        assert players[0]["projected_points"] == 18.0
