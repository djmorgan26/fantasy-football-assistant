"""Leagues that bring themselves up to date.

Before this, a connected league's records, team names and current week were
frozen at whatever they were the moment it was connected, and the only way to
move them was the "Sync Data" button. Nobody should have to press a button to
stop being shown last month's standings.
"""
from datetime import datetime, timedelta, timezone

import pytest

from app.models.league import League, PlatformType
from app.services import freshness

pytestmark = pytest.mark.integration


def league(platform=PlatformType.SLEEPER, *, synced_minutes_ago=None, **kw) -> League:
    last = (
        None if synced_minutes_ago is None
        else datetime.now(timezone.utc) - timedelta(minutes=synced_minutes_ago)
    )
    defaults = {"sleeper_league_id": "123"} if platform == PlatformType.SLEEPER else {}
    return League(id=1, name="A League", platform=platform, last_synced=last,
                  **{**defaults, **kw})


class TestStaleness:
    def test_a_league_just_synced_is_fresh(self):
        assert not freshness.is_stale(league(synced_minutes_ago=1))

    def test_a_league_synced_an_hour_ago_is_not(self):
        assert freshness.is_stale(league(synced_minutes_ago=60))

    def test_a_league_never_synced_counts_as_stale(self):
        # Connect wrote the league but nothing has refreshed it since.
        assert freshness.is_stale(league(synced_minutes_ago=None))

    def test_a_naive_timestamp_is_read_as_utc(self):
        """SQLite hands back naive datetimes; comparing them would explode."""
        row = league()
        row.last_synced = datetime.now(timezone.utc).replace(tzinfo=None)
        assert not freshness.is_stale(row)

    def test_age_is_none_when_it_never_synced(self):
        assert freshness.age(league(synced_minutes_ago=None)) is None


class TestWhatCanRefreshItself:
    def test_sleeper_can(self):
        assert freshness.can_auto_refresh(league(PlatformType.SLEEPER))

    def test_espn_can(self):
        assert freshness.can_auto_refresh(
            league(PlatformType.ESPN, espn_league_id=12345)
        )

    def test_yahoo_cannot_because_it_needs_the_caller_s_token(self):
        assert not freshness.can_auto_refresh(
            league(PlatformType.YAHOO, yahoo_league_key="nfl.l.1")
        )

    def test_a_sleeper_league_with_no_sleeper_id_cannot(self):
        assert not freshness.can_auto_refresh(
            league(PlatformType.SLEEPER, sleeper_league_id=None)
        )


class TestEnsureFresh:
    async def test_a_fresh_league_is_left_alone(self, db_session, mock_mode):
        row = league(synced_minutes_ago=1)
        assert await freshness.ensure_fresh(row, db_session) is False

    async def test_a_platform_that_cannot_refresh_is_left_alone(self, db_session):
        row = league(PlatformType.YAHOO, synced_minutes_ago=None,
                     sleeper_league_id=None, yahoo_league_key="nfl.l.1")
        assert await freshness.ensure_fresh(row, db_session) is False

    async def test_a_stale_league_refreshes_on_read(
        self, client, auth_headers, sleeper_league, mock_mode, db_session
    ):
        from sqlalchemy import select

        row = (await db_session.execute(
            select(League).where(League.id == sleeper_league["league"]["id"])
        )).scalar_one()

        row.last_synced = datetime.now(timezone.utc) - timedelta(hours=2)
        row.current_week = 1
        await db_session.commit()

        assert await freshness.ensure_fresh(row, db_session) is True
        assert not freshness.is_stale(row)

    async def test_a_platform_outage_degrades_rather_than_failing_the_read(
        self, db_session, monkeypatch
    ):
        """Slightly old standings beat an error page."""
        async def explode(*_args, **_kwargs):
            raise RuntimeError("Sleeper is down")

        monkeypatch.setattr(freshness, "_refresh", explode)

        row = league(synced_minutes_ago=None)
        assert await freshness.ensure_fresh(row, db_session) is False

    async def test_a_failure_backs_off_rather_than_retrying_every_request(
        self, db_session, monkeypatch
    ):
        calls = []

        async def explode(*_args, **_kwargs):
            calls.append(1)
            raise RuntimeError("Sleeper is down")

        monkeypatch.setattr(freshness, "_refresh", explode)

        row = league(synced_minutes_ago=None)
        await freshness.ensure_fresh(row, db_session)
        await freshness.ensure_fresh(row, db_session)
        await freshness.ensure_fresh(row, db_session)

        assert len(calls) == 1, "an outage must not become a request storm"
