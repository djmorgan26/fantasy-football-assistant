"""
Vercel serverless entrypoint.

This wraps the canonical FastAPI app (app.main:app) for the Vercel deployment.
The SAME file serves both deployments; the mode is chosen by the MOCK_MODE env
var configured on each Vercel project:

- MOCK demo (MOCK_MODE unset -> defaults to true): runs with no credentials and
  no real API calls. DB is ephemeral SQLite in /tmp (the only writable path on
  Vercel); tables are created and the demo is seeded at cold start, because
  Vercel's Python runtime does not reliably run ASGI lifespan events. Seeding is
  idempotent and deterministic.
- REAL app (MOCK_MODE=false): runs against live ESPN/Sleeper + Groq + a hosted
  Postgres (Supabase). The schema is created once out-of-band (migration), so we
  do NOT create tables or seed here.

Local development is unaffected; it runs backend/app/main.py via uvicorn.
"""
import os
import sys
import asyncio

# Default to mock mode; the real Vercel project sets MOCK_MODE=false explicitly.
os.environ.setdefault("MOCK_MODE", "true")
os.environ.setdefault("MOCK_DATABASE_URL", "sqlite+aiosqlite:////tmp/fantasy_mock.db")
os.environ.setdefault("ALLOWED_ORIGINS", "*")
os.environ.setdefault("DEBUG", "false")

# Make the backend package importable.
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))

from app.core.config import settings  # noqa: E402
from app.main import app  # noqa: E402  (ASGI app Vercel will serve)


if settings.mock_mode:
    # Cold-start init for the mock demo only: create the ephemeral SQLite schema
    # and seed the demo account/leagues. Real mode relies on the hosted Postgres
    # schema created via migration.
    from app.db.database import engine, Base  # noqa: E402
    from app.services.mock_seed import seed_mock_data  # noqa: E402

    async def _initialize() -> None:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        await seed_mock_data()

    try:
        asyncio.run(_initialize())
    except Exception as exc:  # pragma: no cover
        print(f"[vercel mock init] warning: {exc}")
