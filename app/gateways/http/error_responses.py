"""Single place where application errors become HTTP responses."""

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app.schemas.exceptions.application_errors import (
    AccessDeniedError,
    AuthenticationRequiredError,
    ConflictError,
    ExternalServiceError,
    NotFoundError,
    RateLimitedError,
    ValidationFailedError,
)
from app.schemas.exceptions.base_exception import ApplicationError

ERROR_STATUS_CODES: tuple[tuple[type[ApplicationError], int, str], ...] = (
    (NotFoundError, 404, "not_found"),
    (ValidationFailedError, 422, "validation_failed"),
    (ConflictError, 409, "conflict"),
    (AuthenticationRequiredError, 401, "authentication_required"),
    (AccessDeniedError, 403, "access_denied"),
    (RateLimitedError, 429, "rate_limited"),
    (ExternalServiceError, 502, "external_service_error"),
)


def install_error_handlers(http_application: FastAPI) -> None:
    """Register the ApplicationError -> HTTP status mapping on an app."""

    http_application.add_exception_handler(ApplicationError, handle_application_error)


async def handle_application_error(request: Request, error: Exception) -> JSONResponse:
    del request
    status_code: int = 500
    error_code: str = "internal_error"
    for error_type, mapped_status_code, mapped_error_code in ERROR_STATUS_CODES:
        if isinstance(error, error_type):
            status_code = mapped_status_code
            error_code = mapped_error_code
            break

    headers: dict[str, str] = {}
    if status_code == 401:
        headers["WWW-Authenticate"] = "Bearer"

    return JSONResponse(
        status_code=status_code,
        content={"error": error_code, "message": str(error)},
        headers=headers,
    )
