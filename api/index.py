"""
Vercel serverless entrypoint for the PUBLIC MOCK DEMO.

This wraps the canonical FastAPI app (app.main:app) and forces MOCK_MODE so the
deployed demo runs with no external credentials and no real API calls. It is used
ONLY for the Vercel Hobby deployment; local development is unaffected and still
uses backend/app/main.py directly via uvicorn.

Serverless notes:
- The DB lives in /tmp (the only writable path on Vercel) as ephemeral SQLite.
- Table creation + demo seeding run at cold start here, because Vercel's Python
  runtime does not reliably execute ASGI lifespan events. Seeding is idempotent
  and deterministic, so every cold start produces the same demo league + user.
"""
import os
import sys
import asyncio

# Configure mock mode BEFORE importing the app (settings read env at import).
os.environ.setdefault("MOCK_MODE", "true")
os.environ.setdefault("MOCK_DATABASE_URL", "sqlite+aiosqlite:////tmp/fantasy_mock.db")
os.environ.setdefault("SECRET_KEY", "vercel-mock-demo-insecure-key-not-for-production")
os.environ.setdefault("ALLOWED_ORIGINS", "*")
os.environ.setdefault("DEBUG", "false")

# Make the backend package importable.
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))

from app.main import app  # noqa: E402  (ASGI app Vercel will serve)
from app.db.database import engine, Base  # noqa: E402
from app.services.mock_seed import seed_mock_data  # noqa: E402


async def _initialize() -> None:
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    await seed_mock_data()


# Run cold-start initialization once at import time.
try:
    asyncio.run(_initialize())
except Exception as exc:  # pragma: no cover - log and continue; first request may retry
    print(f"[vercel mock init] warning: {exc}")
