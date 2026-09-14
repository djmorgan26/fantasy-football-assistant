"""The shared Sleeper payload caches must not stampede.

Building the league-wide ownership map asks for a roster per team and starts
all of them together. A plain read-then-fetch cache has every one of those
callers miss the empty cache and fetch its own copy of a ~10MB payload, which
is what made one /api/news/league request pull it twelve times and take 6.5
seconds in production.
"""
import asyncio

import pytest

pytestmark = pytest.mark.integration


@pytest.fixture
def service(monkeypatch):
    """A DraftService with empty caches and a counted, slow upstream."""
    from app.services.draft_service import DraftService

    svc = DraftService()
    calls = {"players": 0, "projections": 0}

    async def fake_players():
        calls["players"] += 1
        await asyncio.sleep(0.05)  # long enough that every caller is waiting
        return {"4034": {"full_name": "Patrick Mahomes"}}

    async def fake_projections(season):
        calls["projections"] += 1
        await asyncio.sleep(0.05)
        return {"4034": {"pts_ppr": 300}}

    monkeypatch.setattr(svc.sleeper, "get_all_players", fake_players)
    monkeypatch.setattr(svc.sleeper, "get_player_projections", fake_projections)
    return svc, calls


class TestPlayersCache:
    async def test_twelve_concurrent_callers_fetch_once(self, service):
        svc, calls = service

        results = await asyncio.gather(*(svc.get_players_cached() for _ in range(12)))

        assert calls["players"] == 1, (
            f"{calls['players']} fetches for 12 concurrent callers; the cache is "
            "stampeding again"
        )
        assert all(r == results[0] for r in results)

    async def test_a_later_caller_is_served_from_cache(self, service):
        svc, calls = service

        await svc.get_players_cached()
        await svc.get_players_cached()

        assert calls["players"] == 1

    async def test_an_expired_entry_is_refetched(self, service):
        from datetime import timedelta

        svc, calls = service
        await svc.get_players_cached()

        svc._players_cached_at -= svc._players_ttl + timedelta(seconds=1)
        await svc.get_players_cached()

        assert calls["players"] == 2

    async def test_a_failed_fetch_does_not_poison_the_cache(self, service):
        """The lock must be released on failure, and nothing cached."""
        svc, calls = service

        async def boom():
            calls["players"] += 1
            raise RuntimeError("sleeper down")

        svc.sleeper.get_all_players = boom
        with pytest.raises(RuntimeError):
            await svc.get_players_cached()

        assert svc._players_cache is None
        # A later caller can still try; the lock was not left held.
        await asyncio.wait_for(
            asyncio.gather(svc.get_players_cached(), return_exceptions=True), timeout=2
        )


class TestProjectionsCache:
    async def test_concurrent_callers_fetch_once_per_season(self, service):
        svc, calls = service

        await asyncio.gather(*(svc._get_projections(2026) for _ in range(12)))

        assert calls["projections"] == 1

    async def test_two_seasons_are_cached_separately(self, service):
        svc, calls = service

        await asyncio.gather(svc._get_projections(2026), svc._get_projections(2025))

        assert calls["projections"] == 2


class TestLoopSafety:
    async def test_the_lock_survives_a_new_event_loop(self, service):
        """A reused serverless container can bring a fresh loop with it."""
        from datetime import timedelta

        svc, _ = service
        await svc.get_players_cached()
        first = svc._locks["players"][1]

        # Expire it, so the next call has to take the lock rather than return
        # from cache before ever reaching it.
        svc._players_cached_at -= svc._players_ttl + timedelta(seconds=1)

        # A lock held over from a dead loop would raise rather than serialize.
        def in_a_new_loop():
            return asyncio.run(svc.get_players_cached())

        result = await asyncio.get_running_loop().run_in_executor(None, in_a_new_loop)

        assert result  # the fetch actually completed on the new loop
        assert svc._locks["players"][1] is not first
