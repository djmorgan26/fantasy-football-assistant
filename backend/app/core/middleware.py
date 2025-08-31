import time
import uuid
from fastapi import Request, Response
from fastapi.middleware.base import BaseHTTPMiddleware
from starlette.middleware.base import RequestResponseEndpoint
import structlog
from app.core.config import settings

logger = structlog.get_logger()


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        # Generate request ID
        request_id = str(uuid.uuid4())
        
        # Start timer
        start_time = time.time()
        
        # Get client IP
        client_ip = request.client.host if request.client else "unknown"
        
        # Log request start
        logger.info(
            "Request started",
            request_id=request_id,
            method=request.method,
            url=str(request.url),
            client_ip=client_ip,
            user_agent=request.headers.get("user-agent", "")
        )
        
        # Add request ID to request state
        request.state.request_id = request_id
        
        try:
            response = await call_next(request)
            
            # Calculate response time
            process_time = time.time() - start_time
            
            # Log successful response
            logger.info(
                "Request completed",
                request_id=request_id,
                method=request.method,
                url=str(request.url),
                status_code=response.status_code,
                process_time=round(process_time, 4),
                client_ip=client_ip
            )
            
            # Add headers
            response.headers["X-Request-ID"] = request_id
            response.headers["X-Process-Time"] = str(process_time)
            
            return response
            
        except Exception as e:
            # Calculate response time for errors
            process_time = time.time() - start_time
            
            # Log error
            logger.error(
                "Request failed",
                request_id=request_id,
                method=request.method,
                url=str(request.url),
                error=str(e),
                error_type=type(e).__name__,
                process_time=round(process_time, 4),
                client_ip=client_ip
            )
            
            # Re-raise the exception
            raise


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        response = await call_next(request)
        
        # Add security headers
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        
        if not settings.debug:
            response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        
        return response


class RateLimitingMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, requests_per_minute: int = 60):
        super().__init__(app)
        self.requests_per_minute = requests_per_minute
        self.request_counts = {}
        self.request_times = {}

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        # Get client IP
        client_ip = request.client.host if request.client else "unknown"
        current_time = time.time()
        
        # Clean old entries (older than 1 minute)
        cutoff_time = current_time - 60
        self.request_times = {
            ip: times for ip, times in self.request_times.items()
            if any(t > cutoff_time for t in times)
        }
        
        # Update request times for this IP
        if client_ip not in self.request_times:
            self.request_times[client_ip] = []
        
        # Remove old requests for this IP
        self.request_times[client_ip] = [
            t for t in self.request_times[client_ip] if t > cutoff_time
        ]
        
        # Check rate limit
        if len(self.request_times[client_ip]) >= self.requests_per_minute:
            from fastapi import HTTPException
            logger.warning(
                "Rate limit exceeded",
                client_ip=client_ip,
                requests_in_window=len(self.request_times[client_ip])
            )
            raise HTTPException(
                status_code=429,
                detail="Rate limit exceeded. Too many requests."
            )
        
        # Add current request time
        self.request_times[client_ip].append(current_time)
        
        return await call_next(request)