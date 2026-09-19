"""Keeping a connected league current without anybody pressing a button.

Rosters, scores and the live slate are fetched from the platform on every
request, so they are never stale. What *was* stale is the league's own
furniture — records, points for and against, team names, and the week the
league is on — because only a sync rewrites those, and a sync only ran when
somebody clicked "Sync Data". A Sleeper league connected in September was
still reporting September's records in November.

So a read refreshes it. The first request to touch a league whose stored data
has aged out pays for a refresh; everything for the next `MAX_AGE` is served
from what that wrote. The refresh is deliberately quiet: if the platform is
down or rate-limiting, the read still returns the data we have rather than
failing, because slightly old standings beat an error page.

Yahoo is left out. Its refresh needs the calling user's OAuth token rather
than credentials stored on the league, so it cannot be driven from a league
alone; Yahoo leagues still refresh on demand.
"""
from __future__ import annotations

import asyncio
from datetime import datetime, timedelta, timezone
from typing import Dict, Optional

import structlog
from sqlalchemy import inspect as sa_inspect
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.league import League, PlatformType

logger = structlog.get_logger()

# How old a league's stored data may get before a read refreshes it. Long
# enough that normal browsing does not hammer the platform, short enough that
# a Sunday's records and current week are never meaningfully wrong.
MAX_AGE = timedelta(minutes=10)

# A refresh that fails should not be retried on the very next request, or a
# platform outage turns into a request storm against it.
RETRY_AFTER = timedelta(minutes=2)

# One refresh per league at a time within this process. Two tabs opening at
# once should cost one refresh, not two.
_locks: Dict[int, asyncio.Lock] = {}
_failed_at: Dict[int, datetime] = {}


def _aware(value: Optional[datetime]) -> Optional[datetime]:
    """SQLite hands back naive datetimes; Postgres hands back aware ones."""
    if value is None:
        return None
    return value if value.tzinfo else value.replace(tzinfo=timezone.utc)


def age(league: League) -> Optional[timedelta]:
    """How long since this league was last synced, or None if it never was."""
    last = _aware(league.last_synced)
    return None if last is None else datetime.now(timezone.utc) - last


def is_stale(league: League, max_age: timedelta = MAX_AGE) -> bool:
    """Has the league's stored data aged out? A league never synced has."""
    current = age(league)
    return current is None or current > max_age


def can_auto_refresh(league: League) -> bool:
    """Whether this league can be refreshed from the league row alone."""
    if league.platform == PlatformType.SLEEPER:
        return bool(league.sleeper_league_id)
    if league.platform == PlatformType.ESPN:
        return bool(league.espn_league_id)
    return False  # Yahoo needs the caller's token, so not from here


def _backing_off(league_id: int) -> bool:
    failed = _failed_at.get(league_id)
    return failed is not None and datetime.now(timezone.utc) - failed < RETRY_AFTER


async def _refresh(league: League, db: AsyncSession) -> None:
    if league.platform == PlatformType.SLEEPER:
        from app.services.sleeper_sync import refresh_league as refresh_sleeper

        await refresh_sleeper(league, db)
    else:
        from app.services.espn_sync import refresh_league as refresh_espn

        await refresh_espn(league, db)


async def ensure_fresh(
    league: League, db: AsyncSession, *, max_age: timedelta = MAX_AGE
) -> bool:
    """Refresh the league if its stored data has aged out.

    Returns whether a refresh actually ran. Never raises: a read that cannot
    reach the platform still has the last good data to serve.
    """
    if not can_auto_refresh(league) or not is_stale(league, max_age):
        return False
    if _backing_off(league.id):
        return False

    lock = _locks.setdefault(league.id, asyncio.Lock())
    async with lock:
        # Another request may have refreshed it while this one waited, in which
        # case its commit is already in the database and there is nothing to do.
        # Re-reading only makes sense for a row this session actually tracks.
        if sa_inspect(league).persistent:
            await db.refresh(league)
        if not is_stale(league, max_age) or _backing_off(league.id):
            return False

        try:
            await _refresh(league, db)
        except Exception as e:  # noqa: BLE001 — a stale read beats a failed one
            await db.rollback()
            _failed_at[league.id] = datetime.now(timezone.utc)
            logger.warning(
                "Auto-refresh failed; serving stored data",
                league_id=league.id,
                platform=getattr(league.platform, "value", None),
                error=str(e),
            )
            return False

        _failed_at.pop(league.id, None)
        logger.info(
            "League auto-refreshed on read",
            league_id=league.id,
            platform=getattr(league.platform, "value", None),
        )
        return True
