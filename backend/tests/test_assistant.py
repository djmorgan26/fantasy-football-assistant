"""The Commissioner chat and the weekly primer.

There is no GROQ key in the test environment, so the chat endpoint exercises its
unavailable path. The primer is mostly arithmetic over a roster, so it is tested
for real: the lineup alerts and the best-available swap are the parts anyone
would actually act on.
"""
import pytest

from app.services.llm_service import llm_service

pytestmark = pytest.mark.integration


@pytest.fixture
def captured_llm(monkeypatch):
    """Stand in for the model and keep the prompt it was handed.

    The prompt is the interesting artifact: whether the assistant is grounded
    is entirely a question of what went into it, and asserting on that is far
    more useful than asserting on whatever a model happened to reply.
    """
    calls = []

    def fake_complete(*, system, prompt, temperature, max_tokens, purpose, **kwargs):
        calls.append({
            "system": system,
            "prompt": prompt,
            "purpose": purpose,
            "max_tokens": max_tokens,
        })
        return "Start Reggie Petrov over CeeDee Lamb."

    monkeypatch.setattr(llm_service, "is_available", lambda: True)
    monkeypatch.setattr(llm_service, "complete", fake_complete)
    monkeypatch.setattr(llm_service, "model", "test-model")
    return calls


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


class TestGrounding:
    """What the model is told is the whole ballgame."""

    async def test_the_prompt_carries_real_league_facts(
        self, client, auth_headers, espn_league, mock_mode, captured_llm
    ):
        lid = espn_league["league"]["id"]
        team = espn_league["teams"][0]
        await client.put(f"/api/teams/{team['id']}/claim", headers=auth_headers)

        resp = await client.post(
            f"/api/assistant/{lid}/chat",
            json={"message": "Who should I start?"},
            headers=auth_headers,
        )
        assert resp.status_code == 200
        assert resp.json()["generated_by"] == "test-model"

        prompt = captured_llm[0]["prompt"]
        assert espn_league["league"]["name"] in prompt
        assert team["name"] in prompt
        assert "STANDINGS:" in prompt
        assert "THEIR STARTERS:" in prompt
        assert "THEIR BENCH:" in prompt

        # A real player off the canned roster, not a placeholder.
        from app.services import mock_data
        roster = mock_data.espn_team_roster(team["espn_team_id"], None)["roster"]
        assert roster[0]["full_name"] in prompt

    async def test_it_is_told_not_to_invent_things(
        self, client, auth_headers, espn_league, mock_mode, captured_llm
    ):
        lid = espn_league["league"]["id"]
        await client.post(
            f"/api/assistant/{lid}/chat",
            json={"message": "How am I doing?"},
            headers=auth_headers,
        )
        prompt = captured_llm[0]["prompt"].lower()
        assert "use nothing else" in prompt
        assert "never invent" in captured_llm[0]["system"].lower()

    async def test_the_reply_reports_what_it_was_grounded_on(
        self, client, auth_headers, espn_league, mock_mode, captured_llm
    ):
        lid = espn_league["league"]["id"]
        team = espn_league["teams"][0]
        await client.put(f"/api/teams/{team['id']}/claim", headers=auth_headers)

        body = (await client.post(
            f"/api/assistant/{lid}/chat",
            json={"message": "Who should I start?"},
            headers=auth_headers,
        )).json()

        assert "league settings" in body["grounded_on"]
        assert "standings" in body["grounded_on"]
        assert "your roster" in body["grounded_on"]

    async def test_the_league_voice_reaches_the_prompt(
        self, client, auth_headers, espn_league, mock_mode, captured_llm
    ):
        lid = espn_league["league"]["id"]
        await client.put(
            f"/api/content/{lid}/profile",
            json={"voice_guide": "Speak exclusively in pirate."},
            headers=auth_headers,
        )

        await client.post(
            f"/api/assistant/{lid}/chat",
            json={"message": "Who should I start?"},
            headers=auth_headers,
        )
        assert "Speak exclusively in pirate." in captured_llm[0]["prompt"]

    async def test_board_posts_the_league_liked_become_style_anchors(
        self, client, auth_headers, espn_league, mock_mode, captured_llm
    ):
        """The board feeds the assistant, not just the content generator."""
        lid = espn_league["league"]["id"]
        quote = (
            "Bench Warmers Anonymous started a kicker on bye and still won by thirty. "
            "There is no justice in this league."
        )

        post = await client.post(
            f"/api/board/{lid}/posts", json={"body": quote}, headers=auth_headers
        )
        pid = post.json()["id"]
        for reaction in ("savage", "funny"):
            await client.post(
                f"/api/board/{lid}/posts/{pid}/reactions",
                json={"reaction": reaction},
                headers=auth_headers,
            )

        await client.post(
            f"/api/assistant/{lid}/chat",
            json={"message": "Who should I start?"},
            headers=auth_headers,
        )

        prompt = captured_llm[0]["prompt"]
        assert "HOW THIS LEAGUE ACTUALLY TALKS" in prompt
        assert quote in prompt

    async def test_conversation_history_is_included_but_capped(
        self, client, auth_headers, espn_league, mock_mode, captured_llm
    ):
        lid = espn_league["league"]["id"]
        history = [
            {"role": "user" if i % 2 == 0 else "assistant", "content": f"turn-{i}"}
            for i in range(10)
        ]

        await client.post(
            f"/api/assistant/{lid}/chat",
            json={"message": "And now?", "history": history},
            headers=auth_headers,
        )

        prompt = captured_llm[0]["prompt"]
        assert "CONVERSATION SO FAR:" in prompt
        assert "turn-9" in prompt          # the recent tail survives
        assert "turn-0" not in prompt      # the old head is dropped

    async def test_history_longer_than_the_cap_is_rejected(
        self, client, auth_headers, espn_league, mock_mode
    ):
        lid = espn_league["league"]["id"]
        resp = await client.post(
            f"/api/assistant/{lid}/chat",
            json={
                "message": "hi",
                "history": [{"role": "user", "content": "x"}] * 20,
            },
            headers=auth_headers,
        )
        assert resp.status_code == 422

    async def test_a_model_failure_surfaces_as_502(
        self, client, auth_headers, espn_league, mock_mode, monkeypatch
    ):
        def boom(**kwargs):
            raise RuntimeError("model exploded")

        monkeypatch.setattr(llm_service, "is_available", lambda: True)
        monkeypatch.setattr(llm_service, "complete", boom)

        lid = espn_league["league"]["id"]
        resp = await client.post(
            f"/api/assistant/{lid}/chat",
            json={"message": "Who should I start?"},
            headers=auth_headers,
        )
        assert resp.status_code == 502
        assert "model exploded" not in resp.text

    async def test_the_token_budget_leaves_room_for_reasoning(
        self, client, auth_headers, espn_league, mock_mode, captured_llm
    ):
        """The default Groq model bills its reasoning against max_tokens.

        A tight ceiling does not shorten the answer, it returns nothing at all,
        which is how the news digest silently fell back to a bullet list.
        """
        lid = espn_league["league"]["id"]
        await client.post(
            f"/api/assistant/{lid}/chat",
            json={"message": "Who should I start?"},
            headers=auth_headers,
        )
        assert captured_llm[0]["max_tokens"] >= 1000


class TestPrimerTrashTalk:
    async def test_trash_talk_names_the_real_opponent(
        self, client, auth_headers, espn_league, mock_mode, captured_llm
    ):
        lid = espn_league["league"]["id"]
        team = espn_league["teams"][0]
        await client.put(f"/api/teams/{team['id']}/claim", headers=auth_headers)

        body = (await client.get(
            f"/api/assistant/{lid}/primer", headers=auth_headers
        )).json()

        assert body["trash_talk"]
        prompt = next(c for c in captured_llm if c["purpose"] == "primer_trash_talk")["prompt"]
        assert body["opponent"] in prompt
        assert team["name"] in prompt

    async def test_a_failed_flourish_does_not_break_the_card(
        self, client, auth_headers, espn_league, mock_mode, monkeypatch
    ):
        """The primer is computed; the trash talk is decoration."""
        def boom(**kwargs):
            raise RuntimeError("no")

        monkeypatch.setattr(llm_service, "is_available", lambda: True)
        monkeypatch.setattr(llm_service, "complete", boom)

        lid = espn_league["league"]["id"]
        team = espn_league["teams"][0]
        await client.put(f"/api/teams/{team['id']}/claim", headers=auth_headers)

        resp = await client.get(f"/api/assistant/{lid}/primer", headers=auth_headers)
        assert resp.status_code == 200
        assert resp.json()["trash_talk"] is None
        assert resp.json()["projected"] > 0
