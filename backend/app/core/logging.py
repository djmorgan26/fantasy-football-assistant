import logging
import structlog
from typing import Any, Dict
import traceback
from datetime import datetime
from app.core.config import settings


def configure_logging():
    logging.basicConfig(
        format="%(message)s",
        stream=None,
        level=getattr(logging, settings.log_level.upper()),
    )

    structlog.configure(
        processors=[
            structlog.stdlib.filter_by_level,
            structlog.stdlib.add_logger_name,
            structlog.stdlib.add_log_level,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.dev.ConsoleRenderer()
            if settings.debug
            else structlog.processors.JSONRenderer(),
        ],
        wrapper_class=structlog.stdlib.BoundLogger,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )


class ESPNAPILogger:
    def __init__(self):
        self.logger = structlog.get_logger("espn_api")

    def log_request(self, method: str, url: str, **kwargs):
        self.logger.info(
            "ESPN API Request",
            method=method,
            url=url,
            **kwargs
        )

    def log_response(self, status_code: int, url: str, response_time: float = None, **kwargs):
        self.logger.info(
            "ESPN API Response",
            status_code=status_code,
            url=url,
            response_time=response_time,
            **kwargs
        )

    def log_error(self, error: Exception, context: Dict[str, Any] = None):
        self.logger.error(
            "ESPN API Error",
            error=str(error),
            error_type=type(error).__name__,
            context=context or {},
            traceback=traceback.format_exc() if settings.debug else None
        )


class SecurityLogger:
    def __init__(self):
        self.logger = structlog.get_logger("security")

    def log_login_attempt(self, email: str, success: bool, ip_address: str = None):
        self.logger.info(
            "Login Attempt",
            email=email,
            success=success,
            ip_address=ip_address,
            timestamp=datetime.utcnow().isoformat()
        )

    def log_failed_authentication(self, token: str = None, reason: str = None):
        self.logger.warning(
            "Failed Authentication",
            token_preview=token[:10] + "..." if token else None,
            reason=reason,
            timestamp=datetime.utcnow().isoformat()
        )

    def log_credential_update(self, user_id: int, credential_type: str):
        self.logger.info(
            "Credential Update",
            user_id=user_id,
            credential_type=credential_type,
            timestamp=datetime.utcnow().isoformat()
        )


class DatabaseLogger:
    def __init__(self):
        self.logger = structlog.get_logger("database")

    def log_query_error(self, query: str, error: Exception):
        self.logger.error(
            "Database Query Error",
            query=query[:200] + "..." if len(query) > 200 else query,
            error=str(error),
            error_type=type(error).__name__
        )

    def log_migration_event(self, event: str, version: str = None):
        self.logger.info(
            "Database Migration",
            event=event,
            version=version
        )


# Initialize loggers
espn_logger = ESPNAPILogger()
security_logger = SecurityLogger()
db_logger = DatabaseLogger()