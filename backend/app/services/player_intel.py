"""What is going on with a player right now, in facts rather than prose.

Projections say what a player is worth on average. They say nothing about the
things that actually move a trade: that he is the backup, that he did not
practise Wednesday, that he is 31 in a keeper league, or that there was news
about him this morning. This module gathers exactly those, from sources that
state them as data, so the trade verdict and the model can both use them
without anyone inventing anything.

Where each fact comes from, and why not somewhere else:

- **Sleeper's player index** carries `injury_status`, `injury_body_part`,
  `injury_notes`, `practice_participation`, `depth_chart_order`, `age` and
  `years_exp` per player. It is already downloaded and cached by
  `draft_service`, so this costs nothing extra.
- **ESPN's news wire** tags each article with the athletes it concerns, which
  is how a headline gets attached to a specific player. At `limit=50` the wire
  tags around a hundred distinct players, so a starter in the news will be
  found and a deep bench player will correctly have nothing.
- **ESPN's per-athlete news endpoint** (`/athletes/{id}/news`) looks like the
  right tool and is not: it returns an empty `articles` list for every athlete
  id tried, including players who were on the wire's front page the same
  minute. Do not reach for it again.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, Iterable, List, Optional

import structlog

from app.services import news_service

logger = structlog.get_logger()

# How deep to read the wire when attaching headlines to players. Deep enough
# that a rostered starter in the news is found, shallow enough to stay one
# cached request.
WIRE_DEPTH = 50

# Only headlines this recent are worth showing next to a trade.
MAX_HEADLINE_AGE_DAYS = 14

# Designations that mean something is actually wrong. Sleeper also uses None
# and "Active" for the overwhelming majority of players.
_REAL_INJURY = {"QUESTIONABLE", "DOUBTFUL", "OUT", "IR", "PUP", "SUS", "DNR", "COV"}

_SUFFIXES = {"jr", "sr", "ii", "iii", "iv", "v"}


def _base_name_key(name: str) -> str:
    """`news_service._name_key`, with generational suffixes dropped as well.

    ESPN tags the Vikings running back as "Aaron Jones Sr" and Sleeper calls him
    "Aaron Jones". The existing key normalises punctuation but keeps "sr" as a
    word, so the two never matched and a player in the headlines looked like a
    player with no news.
    """
    key = news_service._name_key(name)
    parts = [p for p in key.split() if p not in _SUFFIXES]
    return " ".join(parts) if len(parts) >= 2 else key


def _role(meta: Dict[str, Any]) -> Optional[str]:
    """Where he sits on his own NFL depth chart, said in words.

    The single most under-used fact in fantasy trade talk: a backup running
    back and the starter ahead of him can carry similar season projections,
    and only one of them is startable next week.
    """
    order = meta.get("depth_chart_order")
    position = meta.get("depth_chart_position") or meta.get("position")
    if not isinstance(order, int) or not position:
        return None
    if order == 1:
        return f"Starting {position}"
    return f"{position}{order} on the depth chart"


def _injury(meta: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    status = (meta.get("injury_status") or "").strip()
    if not status or status.upper() not in _REAL_INJURY:
        return None
    return {
        "status": status,
        "body_part": meta.get("injury_body_part") or None,
        "notes": meta.get("injury_notes") or None,
        "practice": meta.get("practice_participation") or None,
    }


def _recent(article: Dict[str, Any]) -> bool:
    """Drop anything old enough that it is history rather than news."""
    published = article.get("published")
    if not published:
        return True  # undated: keep it and let the UI show no date
    try:
        when = datetime.fromisoformat(str(published).replace("Z", "+00:00"))
        age = (datetime.now(timezone.utc) - when).days
        return age <= MAX_HEADLINE_AGE_DAYS
    except (ValueError, TypeError):
        return True


async def gather(
    players: Iterable[Dict[str, Any]],
    *,
    headlines_per_player: int = 3,
) -> Dict[str, Dict[str, Any]]:
    """Intel for each player, keyed by the player id the caller passed in.

    `players` are roster entries in the app's normalized shape, so this works
    for an ESPN league and a Sleeper one alike: the Sleeper metadata is found by
    name, which is the only id space the two platforms share.

    Never raises. A wire that will not answer costs the headlines and keeps the
    injury and depth-chart facts, because those come from a different source.
    """
    wanted = [p for p in players if p.get("full_name")]
    if not wanted:
        return {}

    meta_by_name = await _sleeper_meta()
    articles = await _wire()

    # Index the wire by the players each article is tagged with, once, rather
    # than scanning every article per player.
    by_player: Dict[str, List[Dict[str, Any]]] = {}
    for article in articles:
        if not _recent(article):
            continue
        for athlete in article.get("athletes") or []:
            by_player.setdefault(_base_name_key(athlete), []).append(article)

    out: Dict[str, Dict[str, Any]] = {}
    for player in wanted:
        key = _base_name_key(player["full_name"])
        meta = meta_by_name.get(key) or {}
        headlines = [
            {
                "headline": a.get("headline"),
                "description": a.get("description"),
                "published": a.get("published"),
                "category": a.get("category"),
                "url": a.get("url"),
            }
            for a in by_player.get(key, [])[:headlines_per_player]
        ]

        out[str(player.get("player_id"))] = {
            "full_name": player["full_name"],
            "role": _role(meta),
            "injury": _injury(meta),
            "age": meta.get("age"),
            "years_exp": meta.get("years_exp"),
            "nfl_team": meta.get("team") or player.get("pro_team_abbr"),
            "headlines": headlines,
        }
    return out


async def _sleeper_meta() -> Dict[str, Dict[str, Any]]:
    """The full Sleeper player payload, keyed by suffix-insensitive name."""
    try:
        from app.services.draft_service import draft_service

        raw = await draft_service.get_players_cached()
    except Exception as e:  # noqa: BLE001 - intel is an enhancement, not a dependency
        logger.warning("Player metadata unavailable for intel", error=str(e))
        return {}

    by_name: Dict[str, Dict[str, Any]] = {}
    for meta in (raw or {}).values():
        if not isinstance(meta, dict):
            continue
        name = meta.get("full_name") or (
            f"{meta.get('first_name', '')} {meta.get('last_name', '')}".strip()
        )
        if name:
            by_name.setdefault(_base_name_key(name), meta)
    return by_name


async def _wire() -> List[Dict[str, Any]]:
    try:
        return await news_service.fetch_news(limit=WIRE_DEPTH)
    except Exception as e:  # noqa: BLE001
        logger.warning("News wire unavailable for intel", error=str(e))
        return []


def flags_from_intel(
    intel: Dict[str, Dict[str, Any]], incoming_ids: Iterable[Any]
) -> List[str]:
    """Risk lines about the players you would be receiving, from the facts.

    Only states what the data says. An injury designation, a backup role, and a
    headline categorised as an injury or transaction are all things the sources
    assert; anything beyond that would be invention.
    """
    flags: List[str] = []
    for player_id in incoming_ids:
        entry = intel.get(str(player_id))
        if not entry:
            continue
        name = entry.get("full_name")

        injury = entry.get("injury")
        if injury:
            line = f"{name} is listed {injury['status']}"
            if injury.get("body_part"):
                line += f" ({injury['body_part']})"
            if injury.get("practice"):
                line += f", practice: {injury['practice']}"
            flags.append(line + ".")

        role = entry.get("role")
        if role and not role.startswith("Starting"):
            flags.append(f"{name} is {role}.")

        for article in entry.get("headlines") or []:
            if article.get("category") in ("Injury", "Transaction"):
                flags.append(
                    f"{article['category']} news on {name}: {article['headline']}"
                )
                break
    return flags
