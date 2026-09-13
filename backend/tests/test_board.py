"""The content board, and the voice loop it feeds.

The point of these tests is the loop: a post the league rates highly has to end
up in the corpus the content generator reads from, and a post the league calls
a cold take has to fall back out of it.
"""
import pytest
from httpx import AsyncClient

pytestmark = pytest.mark.integration

# Long enough to clear the 40-char floor for a usable style anchor.
SAMPLE = (
    "Bench Warmers Anonymous started a kicker on bye and still won by thirty. "
    "There is no justice in this league and I am filing a complaint."
)


async def _post(client, headers, lid, body=SAMPLE, **kwargs):
    resp = await client.post(
        f"/api/board/{lid}/posts",
        json={"body": body, **kwargs},
        headers=headers,
    )
    assert resp.status_code == 201, resp.text
    return resp.json()


class TestPosts:
    async def test_create_and_list(self, client: AsyncClient, auth_headers, espn_league):
        lid = espn_league["league"]["id"]
        created = await _post(client, auth_headers, lid, title="Week 14")

        assert created["title"] == "Week 14"
        assert created["is_ai"] is False
        assert created["is_mine"] is True
        assert created["score"] == 0
        assert created["author_name"] == "Fixture User"

        feed = await client.get(f"/api/board/{lid}/posts", headers=auth_headers)
        assert feed.status_code == 200
        assert [p["id"] for p in feed.json()] == [created["id"]]

    async def test_another_league_cannot_see_it(
        self, client: AsyncClient, auth_headers, espn_league
    ):
        lid = espn_league["league"]["id"]
        await _post(client, auth_headers, lid)

        resp = await client.get(f"/api/board/{lid + 999}/posts", headers=auth_headers)
        assert resp.status_code == 404

    async def test_requires_auth(self, client: AsyncClient, espn_league):
        lid = espn_league["league"]["id"]
        assert (await client.get(f"/api/board/{lid}/posts")).status_code == 401

    async def test_delete_own_post(self, client: AsyncClient, auth_headers, espn_league):
        lid = espn_league["league"]["id"]
        post = await _post(client, auth_headers, lid)

        resp = await client.delete(f"/api/board/{lid}/posts/{post['id']}", headers=auth_headers)
        assert resp.status_code == 204

        feed = await client.get(f"/api/board/{lid}/posts", headers=auth_headers)
        assert feed.json() == []


class TestReactions:
    async def test_toggle_on_and_off(self, client: AsyncClient, auth_headers, espn_league):
        lid = espn_league["league"]["id"]
        post = await _post(client, auth_headers, lid)
        url = f"/api/board/{lid}/posts/{post['id']}/reactions"

        on = await client.post(url, json={"reaction": "savage"}, headers=auth_headers)
        assert on.status_code == 200
        assert on.json()["reactions"]["savage"] == 1
        assert on.json()["my_reactions"] == ["savage"]
        assert on.json()["score"] == 3

        off = await client.post(url, json={"reaction": "savage"}, headers=auth_headers)
        assert off.json()["reactions"]["savage"] == 0
        assert off.json()["my_reactions"] == []
        assert off.json()["score"] == 0

    async def test_reactions_are_weighted(self, client: AsyncClient, auth_headers, espn_league):
        lid = espn_league["league"]["id"]
        post = await _post(client, auth_headers, lid)
        url = f"/api/board/{lid}/posts/{post['id']}/reactions"

        await client.post(url, json={"reaction": "funny"}, headers=auth_headers)   # +3
        resp = await client.post(url, json={"reaction": "smart"}, headers=auth_headers)  # +2
        assert resp.json()["score"] == 5

        cold = await client.post(url, json={"reaction": "cold"}, headers=auth_headers)  # -2
        assert cold.json()["score"] == 3

    async def test_unknown_reaction_rejected(
        self, client: AsyncClient, auth_headers, espn_league
    ):
        lid = espn_league["league"]["id"]
        post = await _post(client, auth_headers, lid)
        resp = await client.post(
            f"/api/board/{lid}/posts/{post['id']}/reactions",
            json={"reaction": "shrug"},
            headers=auth_headers,
        )
        assert resp.status_code == 422


class TestComments:
    async def test_comment_counts_double(self, client: AsyncClient, auth_headers, espn_league):
        lid = espn_league["league"]["id"]
        post = await _post(client, auth_headers, lid)

        resp = await client.post(
            f"/api/board/{lid}/posts/{post['id']}/comments",
            json={"body": "This is the worst thing I have ever read."},
            headers=auth_headers,
        )
        assert resp.status_code == 201
        assert resp.json()["author_name"] == "Fixture User"

        feed = await client.get(f"/api/board/{lid}/posts", headers=auth_headers)
        only = feed.json()[0]
        assert only["comment_count"] == 1
        assert only["score"] == 2          # COMMENT_WEIGHT
        assert len(only["comments"]) == 1

    async def test_threaded_reply(self, client: AsyncClient, auth_headers, espn_league):
        lid = espn_league["league"]["id"]
        post = await _post(client, auth_headers, lid)

        parent = await client.post(
            f"/api/board/{lid}/posts/{post['id']}/comments",
            json={"body": "Bold claim."},
            headers=auth_headers,
        )
        child = await client.post(
            f"/api/board/{lid}/posts/{post['id']}/comments",
            json={"body": "Bolder reply.", "parent_id": parent.json()["id"]},
            headers=auth_headers,
        )
        assert child.json()["parent_id"] == parent.json()["id"]


class TestVoiceLoop:
    """A post the league likes becomes a style anchor; a cold take does not."""

    async def test_high_scoring_post_enters_the_corpus(
        self, client: AsyncClient, auth_headers, espn_league
    ):
        lid = espn_league["league"]["id"]
        post = await _post(client, auth_headers, lid)
        url = f"/api/board/{lid}/posts/{post['id']}/reactions"

        # Below the threshold: one reaction is not evidence of anything.
        await client.post(url, json={"reaction": "smart"}, headers=auth_headers)  # score 2
        samples = await client.get(f"/api/board/{lid}/voice-samples", headers=auth_headers)
        assert samples.json() == []

        await client.post(url, json={"reaction": "savage"}, headers=auth_headers)  # score 5
        samples = await client.get(f"/api/board/{lid}/voice-samples", headers=auth_headers)
        body = samples.json()
        assert len(body) == 1
        assert body[0]["score"] == 5
        assert body[0]["text"].startswith("Bench Warmers Anonymous")
        assert set(body[0]["tags"]) == {"smart", "savage"}

    async def test_cold_reactions_drop_it_back_out(
        self, client: AsyncClient, auth_headers, espn_league
    ):
        lid = espn_league["league"]["id"]
        post = await _post(client, auth_headers, lid)
        url = f"/api/board/{lid}/posts/{post['id']}/reactions"

        await client.post(url, json={"reaction": "savage"}, headers=auth_headers)
        await client.post(url, json={"reaction": "funny"}, headers=auth_headers)  # score 6
        assert len((await client.get(
            f"/api/board/{lid}/voice-samples", headers=auth_headers)).json()) == 1

        await client.post(url, json={"reaction": "cold"}, headers=auth_headers)  # score 4
        await client.post(url, json={"reaction": "funny"}, headers=auth_headers)  # untoggle -> 1
        assert (await client.get(
            f"/api/board/{lid}/voice-samples", headers=auth_headers)).json() == []

    async def test_opting_out_keeps_a_post_out_of_training(
        self, client: AsyncClient, auth_headers, espn_league
    ):
        lid = espn_league["league"]["id"]
        post = await _post(client, auth_headers, lid)
        url = f"/api/board/{lid}/posts/{post['id']}/reactions"
        await client.post(url, json={"reaction": "savage"}, headers=auth_headers)
        await client.post(url, json={"reaction": "funny"}, headers=auth_headers)

        assert len((await client.get(
            f"/api/board/{lid}/voice-samples", headers=auth_headers)).json()) == 1

        resp = await client.patch(
            f"/api/board/{lid}/posts/{post['id']}",
            json={"allow_training": False},
            headers=auth_headers,
        )
        assert resp.status_code == 200
        assert resp.json()["allow_training"] is False
        assert (await client.get(
            f"/api/board/{lid}/voice-samples", headers=auth_headers)).json() == []

    async def test_one_liners_are_never_anchors(
        self, client: AsyncClient, auth_headers, espn_league
    ):
        """Short posts score fine but teach the model nothing."""
        lid = espn_league["league"]["id"]
        post = await _post(client, auth_headers, lid, body="lol")
        url = f"/api/board/{lid}/posts/{post['id']}/reactions"
        await client.post(url, json={"reaction": "savage"}, headers=auth_headers)
        await client.post(url, json={"reaction": "funny"}, headers=auth_headers)

        assert (await client.get(
            f"/api/board/{lid}/voice-samples", headers=auth_headers)).json() == []

    async def test_generated_content_lands_on_the_board(
        self, client: AsyncClient, auth_headers, espn_league, mock_mode
    ):
        """The AI's own output is rated by the league like anything else."""
        lid = espn_league["league"]["id"]

        resp = await client.post(
            f"/api/content/{lid}/generate",
            json={"content_type": "weekly_recap", "week": 14},
            headers=auth_headers,
        )
        assert resp.status_code == 200

        feed = await client.get(f"/api/board/{lid}/posts", headers=auth_headers)
        ai_posts = [p for p in feed.json() if p["is_ai"]]
        assert len(ai_posts) == 1
        assert ai_posts[0]["kind"] == "weekly_recap"
        assert ai_posts[0]["author_name"] == "The Commissioner"
        assert ai_posts[0]["title"] == "Weekly Roast"


class TestStats:
    async def test_stats_roll_up(self, client: AsyncClient, auth_headers, espn_league):
        lid = espn_league["league"]["id"]
        post = await _post(client, auth_headers, lid)
        await client.post(
            f"/api/board/{lid}/posts/{post['id']}/reactions",
            json={"reaction": "funny"},
            headers=auth_headers,
        )
        await client.post(
            f"/api/board/{lid}/posts/{post['id']}/comments",
            json={"body": "Agreed, shameful stuff."},
            headers=auth_headers,
        )

        stats = await client.get(f"/api/board/{lid}/stats", headers=auth_headers)
        assert stats.status_code == 200
        body = stats.json()
        assert body == {
            "posts": 1,
            "comments": 1,
            "reactions": 1,
            "voice_samples": 1,   # score 5 clears the threshold
            "top_reaction": "funny",
        }
