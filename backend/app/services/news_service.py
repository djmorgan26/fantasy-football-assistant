"""
The news layer: the NFL wire, live scores, waiver buzz, and player headshots.

Everything here comes from public, unauthenticated endpoints that both ESPN and
Sleeper serve to their own web clients. No API key, no account, no quota we get
anywhere near. The one expensive call is Sleeper's player dictionary, which ships
14MB of every player who has ever existed; we trim it to the ~3k active fantasy
players once and keep that for a day (see _PlayerIndex).

In mock mode nothing here touches the network — the app has to run with the wifi
off, so each fetch falls back to a small sample set.
"""
from __future__ import annotations

import asyncio
import json
import os
import re
import tempfile
import time
from dataclasses import dataclass, field
from typing import Any, Dict, Iterable, List, Optional

import httpx
import structlog

from app.core.config import settings

logger = structlog.get_logger()

ESPN_NEWS_URL = "https://site.api.espn.com/apis/site/v2/sports/football/nfl/news"
ESPN_SCOREBOARD_URL = "https://site.api.espn.com/apis/site/v2/sports/football/nfl/scoreboard"
SLEEPER_TRENDING_URL = "https://api.sleeper.app/v1/players/nfl/trending/{kind}"
SLEEPER_PLAYERS_URL = "https://api.sleeper.app/v1/players/nfl"

ESPN_HEADSHOT = "https://a.espncdn.com/i/headshots/nfl/players/full/{id}.png"
SLEEPER_HEADSHOT = "https://sleepercdn.com/content/nfl/players/{id}.jpg"

# Sleeper spells team defenses by abbreviation ("PHI"), and their headshot CDN
# serves those from a different path than it does players.
SLEEPER_TEAM_LOGO = "https://sleepercdn.com/images/team_logos/nfl/{abbr}.png"

_PLAYER_CACHE_TTL = 60 * 60 * 24  # a day; rosters don't churn faster than that
_NEWS_CACHE_TTL = 60 * 5          # the wire moves, but not every request
_PLAYER_RETRY_COOLDOWN = 60 * 5   # how long to leave a failing endpoint alone


def headshot_url(espn_player_id: Optional[int] = None,
                 sleeper_player_id: Optional[str] = None,
                 position: Optional[str] = None) -> Optional[str]:
    """Best available headshot for a player, or None to fall back to initials.

    ESPN is preferred: its images are transparent PNGs cut to the shoulders,
    which sit better in a roster row than Sleeper's square crops.
    """
    if position in ("DEF", "D/ST") and sleeper_player_id:
        return SLEEPER_TEAM_LOGO.format(abbr=str(sleeper_player_id).upper())
    if espn_player_id:
        return ESPN_HEADSHOT.format(id=espn_player_id)
    if sleeper_player_id and str(sleeper_player_id).isdigit():
        return SLEEPER_HEADSHOT.format(id=sleeper_player_id)
    return None


@dataclass
class _Cached:
    value: Any = None
    fetched_at: float = 0.0

    def fresh(self, ttl: float) -> bool:
        return self.value is not None and (time.time() - self.fetched_at) < ttl

    def put(self, value: Any) -> Any:
        self.value = value
        self.fetched_at = time.time()
        return value


class _PlayerIndex:
    """Sleeper's player dictionary, trimmed to what a fantasy app actually needs.

    The upstream payload is ~14MB of every player, coach and practice-squad body
    Sleeper has a record of. Filtering to active players at fantasy positions
    leaves about 3,200 entries and 150KB, which is small enough to hold in
    memory and cheap enough to write to the tmp dir so a cold serverless
    instance can reuse the previous one's work.
    """

    def __init__(self) -> None:
        self._by_sleeper_id: Dict[str, dict] = {}
        self._by_name: Dict[str, dict] = {}
        self._fetched_at = 0.0
        # Tracked separately from _fetched_at: a failed attempt leaves the index
        # empty, so a freshness check based on the data alone would let every
        # subsequent request retry immediately and hammer a struggling endpoint.
        self._last_attempt_at = 0.0
        self._lock = asyncio.Lock()

    @property
    def _disk_path(self) -> str:
        return os.path.join(tempfile.gettempdir(), "ffa_sleeper_players.json")

    def _ingest(self, slim: Dict[str, dict]) -> None:
        self._by_sleeper_id = slim
        self._by_name = {_name_key(p["name"]): p for p in slim.values() if p.get("name")}
        self._fetched_at = time.time()

    def _fresh(self) -> bool:
        """Either the data is current, or a recent attempt failed and we wait."""
        now = time.time()
        if self._by_sleeper_id and (now - self._fetched_at) < _PLAYER_CACHE_TTL:
            return True
        return (now - self._last_attempt_at) < _PLAYER_RETRY_COOLDOWN

    async def ensure(self) -> None:
        if self._fresh():
            return
        async with self._lock:
            # Another request may have filled it while we waited for the lock.
            if self._fresh():
                return
            self._last_attempt_at = time.time()

            try:
                on_disk = os.path.getmtime(self._disk_path)
                if (time.time() - on_disk) < _PLAYER_CACHE_TTL:
                    with open(self._disk_path) as fh:
                        self._ingest(json.load(fh))
                    logger.info("Player index loaded from disk cache", players=len(self._by_sleeper_id))
                    return
            except (OSError, ValueError):
                pass

            if settings.mock_mode:
                self._ingest({})
                return

            try:
                async with httpx.AsyncClient(timeout=60) as client:
                    resp = await client.get(SLEEPER_PLAYERS_URL)
                    resp.raise_for_status()
                    raw = resp.json()
            except Exception as e:
                # _last_attempt_at was stamped above, so the cooldown holds.
                logger.warning("Could not refresh the player index", error=str(e))
                return

            slim = {
                pid: {
                    "sleeper_id": pid,
                    "name": p.get("full_name") or p.get("last_name") or "",
                    "position": p.get("position"),
                    "team": p.get("team"),
                    "espn_id": p.get("espn_id"),
                }
                for pid, p in raw.items()
                if p.get("active") and p.get("position") in ("QB", "RB", "WR", "TE", "K", "DEF")
            }
            self._ingest(slim)
            try:
                with open(self._disk_path, "w") as fh:
                    json.dump(slim, fh)
            except OSError:
                pass
            logger.info("Player index refreshed from Sleeper", players=len(slim))

    def by_sleeper_id(self, pid: str) -> Optional[dict]:
        return self._by_sleeper_id.get(str(pid))

    def by_name(self, name: str) -> Optional[dict]:
        return self._by_name.get(_name_key(name))


def _name_key(name: str) -> str:
    """Match names across sources that disagree about punctuation and suffixes.

    ESPN writes "Frank Gore Jr."; Sleeper writes "Frank Gore Jr". Lowercasing and
    dropping everything but letters and spaces makes those the same key.
    """
    cleaned = re.sub(r"[^a-z ]", "", (name or "").lower())
    return re.sub(r"\s+", " ", cleaned).strip()


player_index = _PlayerIndex()


# ----------------------------------------------------------------- the wire

_news_cache: Dict[str, _Cached] = {}


def _cache(key: str) -> _Cached:
    return _news_cache.setdefault(key, _Cached())


def _normalize_article(raw: dict) -> dict:
    """One article, flattened to the fields a news card actually renders."""
    categories = raw.get("categories") or []

    athletes: List[str] = []
    teams: List[str] = []
    for cat in categories:
        if cat.get("type") == "athlete" and cat.get("description"):
            athletes.append(cat["description"])
        elif cat.get("type") == "team" and cat.get("description"):
            teams.append(cat["description"])

    images = raw.get("images") or []
    links = (raw.get("links") or {}).get("web") or {}

    return {
        "id": str(raw.get("id") or raw.get("nowId") or ""),
        "headline": raw.get("headline") or "",
        "description": raw.get("description") or "",
        "byline": raw.get("byline") or "",
        "published": raw.get("published"),
        "image": (images[0].get("url") if images else None),
        "url": links.get("href"),
        "athletes": athletes,
        "teams": teams,
        "category": _primary_category(categories),
    }


def _primary_category(categories: Iterable[dict]) -> str:
    labels = {(c.get("description") or "").lower() for c in categories}
    for needle, label in (
        ("injur", "Injury"),
        ("transaction", "Transaction"),
        ("rumor", "Rumor"),
        ("recap", "Recap"),
    ):
        if any(needle in l for l in labels):
            return label
    return "News"


_SAMPLE_NEWS = [
    {
        "id": "mock-1",
        "headline": "Star RB limited in Friday practice, listed questionable",
        "description": "He took part in individual drills but sat out team periods. The staff called it maintenance.",
        "byline": "Mock Wire",
        "published": None,
        "image": None,
        "url": None,
        "athletes": ["Christian McCaffrey"],
        "teams": ["San Francisco 49ers"],
        "category": "Injury",
    },
    {
        "id": "mock-2",
        "headline": "Backup WR elevated from the practice squad",
        "description": "He is expected to work in three-receiver sets with the starter still sidelined.",
        "byline": "Mock Wire",
        "published": None,
        "image": None,
        "url": None,
        "athletes": ["Reggie Petrov"],
        "teams": ["Philadelphia Eagles"],
        "category": "Transaction",
    },
]


async def fetch_news(limit: int = 40, team_id: Optional[int] = None) -> List[dict]:
    """The NFL wire, newest first."""
    key = f"news:{limit}:{team_id}"
    cached = _cache(key)
    if cached.fresh(_NEWS_CACHE_TTL):
        return cached.value

    if settings.mock_mode:
        return cached.put(list(_SAMPLE_NEWS))

    params: Dict[str, Any] = {"limit": min(limit, 50)}
    if team_id:
        params["team"] = team_id

    try:
        async with httpx.AsyncClient(timeout=20) as client:
            resp = await client.get(ESPN_NEWS_URL, params=params)
            resp.raise_for_status()
            articles = resp.json().get("articles") or []
    except Exception as e:
        logger.warning("News fetch failed", error=str(e))
        return cached.value or []

    return cached.put([_normalize_article(a) for a in articles])


async def fetch_scoreboard() -> List[dict]:
    """Today's games, with enough state to drive a live ticker."""
    cached = _cache("scoreboard")
    if cached.fresh(60):
        return cached.value

    if settings.mock_mode:
        return cached.put([])

    try:
        async with httpx.AsyncClient(timeout=20) as client:
            resp = await client.get(ESPN_SCOREBOARD_URL)
            resp.raise_for_status()
            events = resp.json().get("events") or []
    except Exception as e:
        logger.warning("Scoreboard fetch failed", error=str(e))
        return cached.value or []

    games = []
    for ev in events:
        comp = (ev.get("competitions") or [{}])[0]
        status = ((comp.get("status") or {}).get("type") or {})
        competitors = comp.get("competitors") or []

        def side(home_away: str) -> dict:
            for c in competitors:
                if c.get("homeAway") == home_away:
                    team = c.get("team") or {}
                    return {
                        "abbr": team.get("abbreviation"),
                        "name": team.get("shortDisplayName") or team.get("displayName"),
                        "logo": team.get("logo"),
                        "score": c.get("score"),
                    }
            return {}

        games.append({
            "id": str(ev.get("id")),
            "state": status.get("state"),          # pre | in | post
            "detail": status.get("shortDetail"),
            "home": side("home"),
            "away": side("away"),
        })
    return cached.put(games)


async def fetch_trending(kind: str = "add", hours: int = 24, limit: int = 12) -> List[dict]:
    """Waiver buzz: who the rest of the fantasy world is adding or dropping.

    Sleeper reports raw counts across their entire user base, which is a far
    better signal than any single site's projections — it is what millions of
    managers are actually doing right now.
    """
    key = f"trending:{kind}:{hours}:{limit}"
    cached = _cache(key)
    if cached.fresh(_NEWS_CACHE_TTL):
        return cached.value

    if settings.mock_mode:
        return cached.put([])

    try:
        async with httpx.AsyncClient(timeout=20) as client:
            resp = await client.get(
                SLEEPER_TRENDING_URL.format(kind=kind),
                params={"lookback_hours": hours, "limit": limit},
            )
            resp.raise_for_status()
            rows = resp.json() or []
    except Exception as e:
        logger.warning("Trending fetch failed", error=str(e), kind=kind)
        return cached.value or []

    await player_index.ensure()

    out = []
    for row in rows:
        pid = str(row.get("player_id"))
        player = player_index.by_sleeper_id(pid) or {}
        if not player.get("name"):
            continue
        out.append({
            "sleeper_id": pid,
            "name": player["name"],
            "position": player.get("position"),
            "team": player.get("team"),
            "count": row.get("count", 0),
            "headshot": headshot_url(
                espn_player_id=player.get("espn_id"),
                sleeper_player_id=pid,
                position=player.get("position"),
            ),
        })
    return cached.put(out)


async def resolve_player(name: str) -> Optional[dict]:
    """Look a player up by name across the Sleeper index (for headshots/ids)."""
    await player_index.ensure()
    return player_index.by_name(name)


def relevant_to_roster(article: dict, roster_names: Dict[str, str]) -> Optional[str]:
    """Does this article concern a player somebody in the league rosters?

    Returns the owning team's name when it does, so the news card can say whose
    problem it is. Matching goes through the tagged athlete names ESPN attaches
    to each article, falling back to a headline scan for the cases where it
    tagged the team but not the player.
    """
    for athlete in article.get("athletes", []):
        owner = roster_names.get(_name_key(athlete))
        if owner:
            return owner

    headline = article.get("headline", "")
    for key, owner in roster_names.items():
        # Require the full name; a bare last name matches far too much.
        if len(key) > 8 and key in _name_key(headline):
            return owner
    return None


news_service = None  # module-level functions are the API; kept for symmetry
