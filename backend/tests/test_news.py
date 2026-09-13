"""The news layer: the wire, waiver buzz, and the league-filtered digest.

External HTTP is mocked with respx, the way the rest of the real-mode tests do
it, so nothing here depends on ESPN or Sleeper being up.
"""
import httpx
import pytest
import respx

from app.services import news_service

pytestmark = pytest.mark.integration

ESPN_NEWS_PAYLOAD = {
    "articles": [
        {
            "id": "1",
            "headline": "Josh Allen (shoulder) listed as questionable",
            "description": "He was limited on Friday but is expected to play.",
            "byline": "Wire Staff",
            "published": "2026-09-12T20:34:35Z",
            "images": [{"url": "https://img.example/allen.jpg"}],
            "links": {"web": {"href": "https://espn.example/story/1"}},
            "categories": [
                {"type": "athlete", "description": "Josh Allen"},
                {"type": "team", "description": "Buffalo Bills"},
                {"description": "Injuries"},
            ],
        },
        {
            "id": "2",
            "headline": "Some player nobody in this league rosters was traded",
            "description": "A transaction of no consequence here.",
            "byline": "Wire Staff",
            "published": "2026-09-12T19:00:00Z",
            "images": [],
            "links": {"web": {"href": "https://espn.example/story/2"}},
            "categories": [
                {"type": "athlete", "description": "Nobody Relevant"},
                {"description": "Transactions"},
            ],
        },
    ]
}


@pytest.fixture(autouse=True)
def clear_news_caches():
    """Each test gets a cold cache; otherwise the first mock leaks forward."""
    news_service._news_cache.clear()
    yield
    news_service._news_cache.clear()


class TestHeadshots:
    def test_espn_id_preferred(self):
        url = news_service.headshot_url(espn_player_id=3139477, sleeper_player_id="4034")
        assert url == "https://a.espncdn.com/i/headshots/nfl/players/full/3139477.png"

    def test_falls_back_to_sleeper(self):
        url = news_service.headshot_url(sleeper_player_id="4034")
        assert url == "https://sleepercdn.com/content/nfl/players/4034.jpg"

    def test_defense_uses_the_team_logo(self):
        url = news_service.headshot_url(sleeper_player_id="PHI", position="DEF")
        assert url == "https://sleepercdn.com/images/team_logos/nfl/PHI.png"

    def test_nothing_to_show(self):
        assert news_service.headshot_url() is None


class TestNameMatching:
    def test_punctuation_and_case_are_ignored(self):
        assert news_service._name_key("Frank Gore Jr.") == news_service._name_key("frank gore jr")

    def test_apostrophes_do_not_break_a_match(self):
        assert news_service._name_key("Ja'Marr Chase") == news_service._name_key("JaMarr Chase")


class TestRosterRelevance:
    def test_matches_a_tagged_athlete(self):
        owned = {news_service._name_key("Josh Allen"): "Game of Throws"}
        assert news_service.relevant_to_roster(
            ESPN_NEWS_PAYLOAD["articles"][0], owned
        ) == "Game of Throws"

    def test_returns_none_when_nobody_owns_him(self):
        owned = {news_service._name_key("Josh Allen"): "Game of Throws"}
        assert news_service.relevant_to_roster(ESPN_NEWS_PAYLOAD["articles"][1], owned) is None

    def test_short_names_do_not_match_loosely(self):
        """A bare surname would match half the wire; require the full name."""
        owned = {news_service._name_key("Ali"): "Game of Throws"}
        article = {"athletes": [], "headline": "Coaching staff finalizes plans"}
        assert news_service.relevant_to_roster(article, owned) is None


class TestWireEndpoints:
    @respx.mock
    async def test_wire_normalizes_articles(self, client, auth_headers):
        respx.get(news_service.ESPN_NEWS_URL).mock(
            return_value=httpx.Response(200, json=ESPN_NEWS_PAYLOAD)
        )
        resp = await client.get("/api/news/wire", headers=auth_headers)
        assert resp.status_code == 200

        first = resp.json()["articles"][0]
        assert first["headline"].startswith("Josh Allen")
        assert first["athletes"] == ["Josh Allen"]
        assert first["teams"] == ["Buffalo Bills"]
        assert first["category"] == "Injury"
        assert first["image"] == "https://img.example/allen.jpg"
        assert first["url"] == "https://espn.example/story/1"

    @respx.mock
    async def test_wire_survives_espn_being_down(self, client, auth_headers):
        respx.get(news_service.ESPN_NEWS_URL).mock(return_value=httpx.Response(503))
        resp = await client.get("/api/news/wire", headers=auth_headers)
        assert resp.status_code == 200
        assert resp.json()["articles"] == []

    async def test_wire_requires_auth(self, client):
        assert (await client.get("/api/news/wire")).status_code == 401

    @respx.mock
    async def test_trending_resolves_player_names(self, client, auth_headers):
        respx.get(news_service.SLEEPER_TRENDING_URL.format(kind="add")).mock(
            return_value=httpx.Response(200, json=[{"player_id": "4034", "count": 242829}])
        )
        respx.get(news_service.SLEEPER_PLAYERS_URL).mock(
            return_value=httpx.Response(200, json={
                "4034": {
                    "full_name": "Christian McCaffrey",
                    "position": "RB",
                    "team": "SF",
                    "espn_id": 3117251,
                    "active": True,
                }
            })
        )
        news_service.player_index._fetched_at = 0
        news_service.player_index._by_sleeper_id = {}

        resp = await client.get("/api/news/trending", headers=auth_headers)
        assert resp.status_code == 200

        players = resp.json()["players"]
        assert len(players) == 1
        assert players[0]["name"] == "Christian McCaffrey"
        assert players[0]["count"] == 242829
        assert "3117251" in players[0]["headshot"]


class TestLeagueNews:
    async def test_league_news_flags_who_owns_the_player(
        self, client, auth_headers, espn_league, mock_mode, monkeypatch
    ):
        """The whole point: the wire, annotated with whose problem it is."""
        lid = espn_league["league"]["id"]

        # Borrow a real name off the canned roster so the match is meaningful.
        from app.services import mock_data
        name = mock_data.espn_team_roster(1, 14)["roster"][0]["full_name"]

        wire = [
            {
                "id": "99",
                "headline": f"{name} is dealing with a hamstring issue",
                "description": "Limited in practice.",
                "byline": "Wire Staff",
                "published": "2026-09-12T20:00:00Z",
                "image": None,
                "url": None,
                "athletes": [name],
                "teams": [],
                "category": "Injury",
            },
            {
                "id": "100",
                "headline": "A player nobody here rosters signs an extension",
                "description": "Of no consequence to this league.",
                "byline": "Wire Staff",
                "published": "2026-09-12T19:00:00Z",
                "image": None,
                "url": None,
                "athletes": ["Nobody Relevant"],
                "teams": [],
                "category": "Transaction",
            },
        ]

        async def fake_news(**kwargs):
            return wire

        monkeypatch.setattr(news_service, "fetch_news", fake_news)

        resp = await client.get(f"/api/news/league/{lid}", headers=auth_headers)
        assert resp.status_code == 200
        body = resp.json()

        assert body["rostered_count"] == 1
        # League-relevant news sorts to the top.
        assert body["articles"][0]["id"] == "99"
        assert body["articles"][0]["rostered_by"] is not None
        assert body["articles"][1]["rostered_by"] is None

    async def test_league_news_404s_for_a_league_you_do_not_own(self, client, auth_headers):
        assert (await client.get("/api/news/league/9999", headers=auth_headers)).status_code == 404

    async def test_digest_says_so_when_nothing_is_relevant(
        self, client, auth_headers, espn_league, mock_mode, monkeypatch
    ):
        lid = espn_league["league"]["id"]

        async def fake_news(**kwargs):
            return [{
                "id": "1",
                "headline": "Nobody Relevant signs an extension",
                "description": "Not a player in this league.",
                "byline": "Wire",
                "published": None,
                "image": None,
                "url": None,
                "athletes": ["Nobody Relevant"],
                "teams": [],
                "category": "Transaction",
            }]

        monkeypatch.setattr(news_service, "fetch_news", fake_news)

        resp = await client.get(f"/api/news/digest/{lid}", headers=auth_headers)
        assert resp.status_code == 200
        assert "Quiet day" in resp.json()["digest"]
        assert resp.json()["items"] == []

    async def test_digest_falls_back_to_a_list_without_an_llm(
        self, client, auth_headers, espn_league, mock_mode
    ):
        """No GROQ key in tests, so the digest must still say something useful.

        Mock mode's sample wire deliberately names players on the canned roster,
        so the demo shows a real annotated digest rather than an empty state.
        """
        lid = espn_league["league"]["id"]
        resp = await client.get(f"/api/news/digest/{lid}", headers=auth_headers)
        assert resp.status_code == 200

        body = resp.json()
        assert body["generated_by"] == "fallback"
        assert body["items"], "mock wire should match the mock roster"
        assert all(item["rostered_by"] for item in body["items"])

    async def test_digest_can_publish_to_the_board(
        self, client, auth_headers, espn_league, mock_mode
    ):
        lid = espn_league["league"]["id"]
        resp = await client.get(
            f"/api/news/digest/{lid}?publish=true", headers=auth_headers
        )
        assert resp.status_code == 200

        feed = await client.get(f"/api/board/{lid}/posts", headers=auth_headers)
        digests = [p for p in feed.json() if p["kind"] == "digest"]
        assert len(digests) == 1
        assert digests[0]["is_ai"] is True
