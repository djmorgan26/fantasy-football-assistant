"""The Commissioner chat and the weekly primer.

There is no GROQ key in the test environment, so the chat endpoint exercises its
unavailable path. The primer is mostly arithmetic over a roster, so it is tested
for real: the lineup alerts and the best-available swap are the parts anyone
would actually act on.
"""
import pytest

pytestmark = pytest.mark.integration


class TestSuggestions:
    async def test_chips_name_real_things(self, client, auth_headers, espn_league, mock_mode):
        """Generic chips get ignored; ones naming your actual players get tapped."""
        lid = espn_league["league"]["id"]

        # Claim a team so the assistant knows whose roster to look at.
        team_id = espn_league["teams"][0]["id"]
        claimed = await client.put(f"/api/teams/{team_id}/claim", headers=auth_headers)
        assert claimed.status_code == 200

        resp = await client.get(f"/api/assistant/{lid}/suggestions", headers=auth_headers)
        assert resp.status_code == 200

        chips = resp.json()["suggestions"]
        assert 1 <= len(chips) <= 5
        assert "Who should I start this week?" in chips
        # At least one chip should reference something specific, not boilerplate.
        assert any(c != "Who should I start this week?" for c in chips)

    async def test_suggestions_work_without_a_claimed_team(
        self, client, auth_headers, espn_league, mock_mode
    ):
        lid = espn_league["league"]["id"]
        resp = await client.get(f"/api/assistant/{lid}/suggestions", headers=auth_headers)
        assert resp.status_code == 200
        assert resp.json()["suggestions"]

    async def test_404_for_someone_elses_league(self, client, auth_headers):
        resp = await client.get("/api/assistant/9999/suggestions", headers=auth_headers)
        assert resp.status_code == 404


class TestChat:
    async def test_says_so_when_the_model_is_not_configured(
        self, client, auth_headers, espn_league, mock_mode
    ):
        lid = espn_league["league"]["id"]
        resp = await client.post(
            f"/api/assistant/{lid}/chat",
            json={"message": "Who should I start?"},
            headers=auth_headers,
        )
        assert resp.status_code == 200
        assert resp.json()["generated_by"] == "unavailable"
        assert "GROQ_API_KEY" in resp.json()["reply"]

    async def test_rejects_an_empty_message(self, client, auth_headers, espn_league, mock_mode):
        lid = espn_league["league"]["id"]
        resp = await client.post(
            f"/api/assistant/{lid}/chat", json={"message": ""}, headers=auth_headers
        )
        assert resp.status_code == 422

    async def test_requires_auth(self, client, espn_league):
        lid = espn_league["league"]["id"]
        resp = await client.post(f"/api/assistant/{lid}/chat", json={"message": "hi"})
        assert resp.status_code == 401


class TestPrimer:
    async def test_needs_a_claimed_team(self, client, auth_headers, espn_league, mock_mode):
        lid = espn_league["league"]["id"]
        resp = await client.get(f"/api/assistant/{lid}/primer", headers=auth_headers)
        assert resp.status_code == 400
        assert "Claim your team" in resp.json()["detail"]

    async def test_primer_reports_the_week(self, client, auth_headers, espn_league, mock_mode):
        lid = espn_league["league"]["id"]
        team = espn_league["teams"][0]
        await client.put(f"/api/teams/{team['id']}/claim", headers=auth_headers)

        resp = await client.get(f"/api/assistant/{lid}/primer", headers=auth_headers)
        assert resp.status_code == 200

        body = resp.json()
        assert body["team_name"] == team["name"]
        assert body["week"] >= 1
        assert body["starters"] > 0
        assert body["projected"] > 0
        assert isinstance(body["alerts"], list)
        # No LLM in tests, so the optional flourish is absent, not broken.
        assert body["trash_talk"] is None

    async def test_alerts_only_cover_starters(
        self, client, auth_headers, espn_league, mock_mode
    ):
        lid = espn_league["league"]["id"]
        team = espn_league["teams"][0]
        await client.put(f"/api/teams/{team['id']}/claim", headers=auth_headers)

        resp = await client.get(f"/api/assistant/{lid}/primer", headers=auth_headers)
        alerts = resp.json()["alerts"]

        from app.services import mock_data
        roster = mock_data.espn_team_roster(team["espn_team_id"], None)["roster"]
        starters = {p["full_name"] for p in roster if p.get("is_starter")}

        for alert in alerts:
            assert alert["player"] in starters
            assert alert["severity"] in ("out", "questionable")

    async def test_best_swap_is_a_real_improvement(
        self, client, auth_headers, espn_league, mock_mode
    ):
        """If a swap is suggested it has to gain points, not lose them."""
        lid = espn_league["league"]["id"]
        team = espn_league["teams"][0]
        await client.put(f"/api/teams/{team['id']}/claim", headers=auth_headers)

        resp = await client.get(f"/api/assistant/{lid}/primer", headers=auth_headers)
        swap = resp.json()["best_swap"]

        if swap is not None:
            assert swap["gain"] > 0.5
            assert swap["start"] != swap["sit"]
            assert swap["slot"]
