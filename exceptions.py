"""
Domain exceptions and global exception handlers.

Provides a small hierarchy of application-specific errors and a helper to
register FastAPI exception handlers that return clean, consistent JSON
responses without leaking stack traces or internal details.
"""

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from schemas import ErrorResponse


class ApplicationError(Exception):
    """Base class for all application-specific errors."""

    status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR
    code: str = "internal_error"

    def __init__(self, detail: str, *, status_code: int | None = None, code: str | None = None):
        super().__init__(detail)
        self.detail = detail
        if status_code is not None:
            self.status_code = status_code
        if code is not None:
            self.code = code


class GeminiAPIError(ApplicationError):
    """Raised when the Gemini SDK returns an error or cannot be reached."""

    status_code = status.HTTP_502_BAD_GATEWAY
    code = "gemini_api_error"


class DatabaseError(ApplicationError):
    """Raised when a database operation fails."""

    status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
    code = "database_error"


class ConfigurationError(ApplicationError):
    """Raised when a required configuration value is missing or invalid."""

    status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
    code = "configuration_error"


def _error_response(status_code: int, code: str, detail: str) -> JSONResponse:
    return JSONResponse(
        status_code=status_code,
        content=ErrorResponse(code=code, detail=detail).model_dump(),
    )


async def request_validation_error_handler(
    request: Request,
    exc: RequestValidationError,
) -> JSONResponse:
    """Return a structured 422 response for Pydantic validation errors."""
    return _error_response(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        code="validation_error",
        detail=str(exc),
    )


async def application_error_handler(request: Request, exc: ApplicationError) -> JSONResponse:
    """Handle all domain-specific application errors."""
    return _error_response(
        status_code=exc.status_code,
        code=exc.code,
        detail=exc.detail,
    )


async def generic_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Catch-all handler to avoid leaking stack traces or internal details."""
    return _error_response(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        code="internal_error",
        detail="An unexpected error occurred. Please try again later.",
    )


def register_exception_handlers(app: FastAPI) -> None:
    """Attach global exception handlers to the FastAPI application."""
    app.add_exception_handler(RequestValidationError, request_validation_error_handler)
    app.add_exception_handler(ApplicationError, application_error_handler)
    app.add_exception_handler(Exception, generic_exception_handler)
