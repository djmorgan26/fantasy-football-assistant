"""
The things a service needs once real people depend on it: a request id on every
request, one line of structured access log per request, security headers, and
an error handler that never leaks a stack trace to a browser.

This replaces three modules (`core/exceptions.py`, `core/logging.py`,
`core/middleware.py`) that shipped with the repo but were imported by nothing —
they were never wired into the app, so none of it ever ran. Everything here is
installed by `install_observability()` in app/main.py and covered by tests.
"""
from __future__ import annotations

import os
import time
import uuid
from contextvars import ContextVar
from typing import Awaitable, Callable

import structlog
from fastapi import FastAPI, Request, Response
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

logger = structlog.get_logger()

REQUEST_ID_HEADER = "X-Request-ID"

# The current request's id, so a log line written deep in a service can be tied
# back to the request that caused it without threading an argument through
# every call.
request_id_ctx: ContextVar[str] = ContextVar("request_id", default="")


def current_request_id() -> str:
    return request_id_ctx.get()


def build_info() -> dict:
    """What is actually running, for the health endpoints to report.

    Vercel injects the commit sha at build time; locally there is none, and
    saying "dev" is more honest than inventing one.
    """
    sha = (
        os.getenv("VERCEL_GIT_COMMIT_SHA")
        or os.getenv("GIT_COMMIT_SHA")
        or ""
    )
    return {
        "commit": sha[:12] if sha else "dev",
        "region": os.getenv("VERCEL_REGION") or os.getenv("FLY_REGION") or "local",
        "environment": os.getenv("VERCEL_ENV") or os.getenv("APP_ENV") or "development",
    }


class RequestContextMiddleware(BaseHTTPMiddleware):
    """Tag every request with an id and log one line when it finishes.

    The id is taken from the incoming header when a proxy already set one, so a
    trace survives across hops, and echoed back on the response so a user can
    quote it in a bug report.
    """

    # Noise that would otherwise dominate the log. Health checks run constantly.
    QUIET_PATHS = {"/health", "/health/live", "/health/ready", "/favicon.ico"}

    async def dispatch(
        self, request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        request_id = request.headers.get(REQUEST_ID_HEADER) or uuid.uuid4().hex[:16]
        token = request_id_ctx.set(request_id)
        started = time.perf_counter()

        try:
            response = await call_next(request)
        except Exception:
            # Log it here, where the request context still exists, then let the
            # exception handler below turn it into a response.
            logger.exception(
                "Request failed",
                request_id=request_id,
                method=request.method,
                path=request.url.path,
                duration_ms=round((time.perf_counter() - started) * 1000, 2),
            )
            request_id_ctx.reset(token)
            raise

        duration_ms = round((time.perf_counter() - started) * 1000, 2)
        response.headers[REQUEST_ID_HEADER] = request_id
        response.headers["Server-Timing"] = f"app;dur={duration_ms}"

        if request.url.path not in self.QUIET_PATHS:
            log = logger.warning if response.status_code >= 500 else logger.info
            log(
                "Request handled",
                request_id=request_id,
                method=request.method,
                path=request.url.path,
                status=response.status_code,
                duration_ms=duration_ms,
            )

        request_id_ctx.reset(token)
        return response


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Headers a browser should get on every response.

    No Content-Security-Policy here: the API serves JSON and the built SPA,
    and a CSP tight enough to be worth having would need to know about the
    frontend's own asset hashes. That belongs in the hosting config.
    """

    async def dispatch(
        self, request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        response = await call_next(request)
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("X-Frame-Options", "DENY")
        response.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
        response.headers.setdefault(
            "Permissions-Policy", "geolocation=(), microphone=(), camera=()"
        )
        return response


async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Turn an unexpected crash into a JSON body the frontend can render.

    The frontend's axios interceptor reads `detail`, so this keeps that shape
    rather than inventing a second error format. The message is deliberately
    generic — the detail is in the logs, keyed by the request id, which is the
    one thing worth handing the user.
    """
    request_id = current_request_id() or "unknown"
    return JSONResponse(
        status_code=500,
        content={
            "detail": "Something went wrong on our end. Try again in a moment.",
            "request_id": request_id,
        },
        headers={REQUEST_ID_HEADER: request_id},
    )


def install_observability(app: FastAPI) -> None:
    """Wire the middleware and the catch-all handler onto the app.

    Order matters: middleware added later runs first, so the request-id
    middleware goes on last and therefore wraps everything — including the
    security headers — and every log line it writes has an id.
    """
    app.add_middleware(SecurityHeadersMiddleware)
    app.add_middleware(RequestContextMiddleware)
    app.add_exception_handler(Exception, unhandled_exception_handler)
