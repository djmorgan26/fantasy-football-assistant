from fastapi import FastAPI, HTTPException
from sqlalchemy import text
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.staticfiles import StaticFiles
from contextlib import asynccontextmanager
import structlog
import os
from pathlib import Path
from app.core.config import settings
from app.db.database import engine, Base
from app.api import (
    auth, leagues, teams, players, trades, suggestions, sleeper_leagues,
    weekly_recap, draft, content, board, news, assistant, health, gameday,
    portfolio, actions, yahoo,
)
from app.core.observability import install_observability

# Configure structured logging
structlog.configure(
    processors=[
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
        structlog.processors.JSONRenderer()
    ],
    context_class=dict,
    logger_factory=structlog.stdlib.LoggerFactory(),
    cache_logger_on_first_use=True,
)

logger = structlog.get_logger()


async def ensure_additive_schema(conn) -> None:
    """Bridge deployments originally created with ``create_all`` to new columns.

    Early production databases predate Alembic being usable and therefore have
    no revision history. ``create_all`` creates missing tables but deliberately
    never alters existing ones, which made a Google sign-in try to read
    ``users.google_sub`` from an older database and return 500. These are all
    additive, idempotent PostgreSQL operations. Alembic remains the canonical
    schema history; this makes a rolling serverless deployment safe until it
    has been stamped and migrated.
    """
    if conn.dialect.name != "postgresql":
        return

    statements = (
        "ALTER TABLE users ADD COLUMN IF NOT EXISTS google_sub VARCHAR(255)",
        "ALTER TABLE users ADD COLUMN IF NOT EXISTS avatar_url TEXT",
        "ALTER TABLE users ALTER COLUMN hashed_password DROP NOT NULL",
        "CREATE UNIQUE INDEX IF NOT EXISTS ix_users_google_sub ON users (google_sub)",
        "ALTER TABLE users ADD COLUMN IF NOT EXISTS yahoo_access_token_encrypted TEXT",
        "ALTER TABLE users ADD COLUMN IF NOT EXISTS yahoo_refresh_token_encrypted TEXT",
        "ALTER TABLE users ADD COLUMN IF NOT EXISTS yahoo_token_expires_at TIMESTAMP WITH TIME ZONE",
        "ALTER TABLE users ADD COLUMN IF NOT EXISTS yahoo_guid VARCHAR(255)",
        "ALTER TABLE leagues ADD COLUMN IF NOT EXISTS yahoo_league_key VARCHAR(255)",
        "ALTER TABLE leagues ADD COLUMN IF NOT EXISTS yahoo_user_guid VARCHAR(255)",
        "CREATE INDEX IF NOT EXISTS ix_leagues_yahoo_league_key ON leagues (yahoo_league_key)",
        "ALTER TABLE teams ADD COLUMN IF NOT EXISTS yahoo_team_key VARCHAR(255)",
    )
    for statement in statements:
        await conn.execute(text(statement))

    # The enum already exists in the legacy database, so SQLAlchemy cannot add
    # this value. PostgreSQL 12+ supports IF NOT EXISTS, making the statement
    # safe across cold starts and concurrent Vercel instances.
    await conn.execute(text("ALTER TYPE platformtype ADD VALUE IF NOT EXISTS 'YAHOO'"))


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logger.info("Starting Fantasy Football Assistant API", version=settings.app_version)
    
    # Create database tables
    try:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
            await ensure_additive_schema(conn)
        logger.info("Database tables created successfully")
    except Exception as e:
        logger.error("Failed to create database tables", error=str(e))
        raise

    # In mock/demo mode, seed a ready-to-use demo account + sample leagues.
    if settings.mock_mode:
        logger.info("MOCK_MODE enabled — seeding demo data (no external APIs will be called)")
        try:
            from app.services.mock_seed import seed_mock_data
            await seed_mock_data()
        except Exception as e:
            logger.error("Failed to seed mock data", error=str(e))

    yield
    
    # Shutdown
    logger.info("Shutting down Fantasy Football Assistant API")
    await engine.dispose()


# Create FastAPI application
app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="A comprehensive Fantasy Football assistant that integrates with ESPN leagues",
    docs_url="/docs" if settings.debug else None,
    redoc_url="/redoc" if settings.debug else None,
    lifespan=lifespan
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins.split(",") if settings.allowed_origins else ["*"],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["*"],
)

# Trusted host middleware for production (skip in mock mode so the public demo
# can be served from any host). Hosts are configurable via ALLOWED_HOSTS and
# default to localhost + *.vercel.app so the real Vercel deployment works.
if not settings.debug and not settings.mock_mode:
    hosts = [h.strip() for h in settings.allowed_hosts.split(",") if h.strip()] or ["*"]
    app.add_middleware(TrustedHostMiddleware, allowed_hosts=hosts)


# Public app metadata (no auth) — lets the frontend show a demo banner + creds.
@app.get("/api/meta")
async def app_meta():
    meta = {
        "mock_mode": settings.mock_mode,
        "app_name": settings.app_name,
        "version": settings.app_version,
        # Public by design: the client id ships in any page that renders a
        # Google button. Serving it here rather than baking it into the
        # frontend build means rotating it takes an env var change, not a
        # redeploy of the static assets. Empty string = Google sign-in off,
        # and the frontend hides the button rather than rendering a broken one.
        "google_client_id": settings.google_client_id,
    }
    if settings.mock_mode:
        from app.services import mock_data
        meta["demo_credentials"] = {
            "email": mock_data.DEMO_USER_EMAIL,
            "password": mock_data.DEMO_USER_PASSWORD,
        }
    return meta


# Request ids, access logs, security headers, and a JSON body for unhandled
# errors. Installed before the routers so it wraps every one of them.
install_observability(app)


# Health probes are unprefixed: /health, /health/live, /health/ready.
app.include_router(health.router)

# Include API routers
app.include_router(auth.router, prefix="/api")
app.include_router(leagues.router, prefix="/api")
app.include_router(sleeper_leagues.router, prefix="/api")
app.include_router(teams.router, prefix="/api")
app.include_router(players.router, prefix="/api")
app.include_router(trades.router, prefix="/api")
app.include_router(suggestions.router, prefix="/api")
app.include_router(weekly_recap.router, prefix="/api")
app.include_router(draft.router, prefix="/api")
app.include_router(content.router, prefix="/api")
app.include_router(board.router, prefix="/api")
app.include_router(news.router, prefix="/api")
app.include_router(assistant.router, prefix="/api")
app.include_router(gameday.router, prefix="/api")
app.include_router(portfolio.router, prefix="/api")
app.include_router(actions.router, prefix="/api")
app.include_router(yahoo.router, prefix="/api")


# ESPN service health check
@app.get("/api/espn/health")
async def espn_health():
    try:
        from app.services.espn_service import ESPNService
        espn_service = ESPNService()
        
        # Try to make a simple request to ESPN (using a public league for testing)
        # This is just a basic connectivity check
        import httpx
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(f"{espn_service.base_url}/seasons/2024/segments/0/leagues/123456")
            # We expect this to fail with 404, but that means the service is reachable
            
        return {
            "espn_service": "reachable",
            "base_url": espn_service.base_url
        }
    except httpx.ConnectTimeout:
        return {
            "espn_service": "unreachable - timeout",
            "base_url": espn_service.base_url
        }
    except Exception as e:
        return {
            "espn_service": "error",
            "error": str(e)
        }


# Mount static files for frontend
frontend_dist_path = Path(__file__).parent.parent.parent / "frontend" / "dist"
if frontend_dist_path.exists():
    app.mount("/", StaticFiles(directory=str(frontend_dist_path), html=True), name="frontend")


# Global exception handler
@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    logger.error(
        "Unhandled exception",
        path=str(request.url.path),
        method=request.method,
        error=str(exc),
        exc_info=True
    )
    return HTTPException(
        status_code=500,
        detail="An unexpected error occurred"
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.reload,
        log_level=settings.log_level.lower()
    )
