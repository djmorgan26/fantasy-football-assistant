"""
Health endpoints.

Two of them, because they answer different questions and a load balancer needs
both:

  /health/live   — is the process up? Never touches a dependency, so a database
                   blip cannot get the container killed and restarted into the
                   same blip.
  /health/ready  — should this instance receive traffic? Checks the database
                   for real and returns 503 when it cannot serve.

/health stays as an alias of the liveness probe because existing deployments
and the Vercel config already point at it.
"""
import asyncio
import time
from typing import Any, Dict

import structlog
from fastapi import APIRouter, Response, status
from sqlalchemy import text

from app.core.config import settings
from app.core.observability import build_info
from app.db.database import SessionLocal

logger = structlog.get_logger()
router = APIRouter(tags=["health"])

# A readiness probe that hangs is worse than one that fails: the checker itself
# has a deadline, so a wedged database surfaces as "not ready" rather than a
# request that never returns.
DB_CHECK_TIMEOUT_SECONDS = 5.0

_STARTED_AT = time.time()


def _base() -> Dict[str, Any]:
    return {
        "app": settings.app_name,
        "version": settings.app_version,
        "mock_mode": settings.mock_mode,
        **build_info(),
    }


@router.get("/health/live")
@router.get("/health")
async def live() -> Dict[str, Any]:
    """Liveness. Cheap on purpose — no I/O, no dependencies."""
    return {
        "status": "ok",
        "uptime_seconds": round(time.time() - _STARTED_AT, 1),
        **_base(),
    }


async def _check_database() -> Dict[str, Any]:
    started = time.perf_counter()
    try:
        async with asyncio.timeout(DB_CHECK_TIMEOUT_SECONDS):
            async with SessionLocal() as session:
                await session.execute(text("SELECT 1"))
        return {"status": "ok", "latency_ms": round((time.perf_counter() - started) * 1000, 2)}
    except asyncio.TimeoutError:
        return {"status": "timeout", "timeout_seconds": DB_CHECK_TIMEOUT_SECONDS}
    except Exception as e:
        logger.warning("Readiness database check failed", error=str(e))
        return {"status": "error", "error": type(e).__name__}


@router.get("/health/ready")
async def ready(response: Response) -> Dict[str, Any]:
    """Readiness. The database is the only hard dependency.

    ESPN, Sleeper and Groq being down degrade features but do not make the
    instance unfit for traffic, so they are reported and never fail the probe.
    """
    database = await _check_database()

    # Reported, not gated. A missing model key means recaps fall back to facts;
    # it is not a reason to pull an instance out of rotation.
    features = {
        "llm": "configured" if settings.groq_api_key else "not_configured",
        "espn": "mock" if settings.mock_mode else "live",
        "sleeper": "mock" if settings.mock_mode else "live",
    }

    healthy = database["status"] == "ok"
    if not healthy:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE

    return {
        "status": "ready" if healthy else "not_ready",
        "checks": {"database": database},
        "features": features,
        **_base(),
    }
