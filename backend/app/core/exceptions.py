from fastapi import HTTPException, status
from typing import Any, Dict, Optional


class FantasyFootballException(Exception):
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        self.message = message
        self.details = details or {}
        super().__init__(self.message)


class ESPNServiceException(FantasyFootballException):
    pass


class AuthenticationException(FantasyFootballException):
    pass


class AuthorizationException(FantasyFootballException):
    pass


class ValidationException(FantasyFootballException):
    pass


class DatabaseException(FantasyFootballException):
    pass


# HTTP Exception factories
def create_http_exception(
    status_code: int,
    detail: str,
    headers: Optional[Dict[str, str]] = None
) -> HTTPException:
    return HTTPException(
        status_code=status_code,
        detail=detail,
        headers=headers
    )


def create_validation_error(message: str) -> HTTPException:
    return create_http_exception(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        detail=message
    )


def create_authentication_error(message: str = "Authentication failed") -> HTTPException:
    return create_http_exception(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail=message,
        headers={"WWW-Authenticate": "Bearer"}
    )


def create_authorization_error(message: str = "Not authorized") -> HTTPException:
    return create_http_exception(
        status_code=status.HTTP_403_FORBIDDEN,
        detail=message
    )


def create_not_found_error(message: str = "Resource not found") -> HTTPException:
    return create_http_exception(
        status_code=status.HTTP_404_NOT_FOUND,
        detail=message
    )


def create_espn_service_error(message: str = "ESPN service unavailable") -> HTTPException:
    return create_http_exception(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        detail=message
    )


def create_server_error(message: str = "Internal server error") -> HTTPException:
    return create_http_exception(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail=message
    )