"""
Single place where application errors become HTTP responses.

Every error body is an `ErrorBody`: {"error": "<code>", "message": "<English
text>"}. When the error carries machine-readable reasons
(`ApplicationError.reasons`), the body also has "reasons": [{"code",
"message", "details"}, ...], e.g. the failed go-live checks of a refused
publish (409) or why a menu link could not be read (422). The field is
absent otherwise, and clients that do not know it ignore it.
"""

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app.schemas.constants.errors import ApiErrorCode
from app.schemas.dto.errors import ErrorBody
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
from app.schemas.typings.platform.strings import ErrorMessageText

ERROR_STATUS_CODES: tuple[tuple[type[ApplicationError], int, ApiErrorCode], ...] = (
    (NotFoundError, 404, ApiErrorCode.NOT_FOUND),
    (ValidationFailedError, 422, ApiErrorCode.VALIDATION_FAILED),
    (ConflictError, 409, ApiErrorCode.CONFLICT),
    (AuthenticationRequiredError, 401, ApiErrorCode.AUTHENTICATION_REQUIRED),
    (AccessDeniedError, 403, ApiErrorCode.ACCESS_DENIED),
    (RateLimitedError, 429, ApiErrorCode.RATE_LIMITED),
    (ExternalServiceError, 502, ApiErrorCode.EXTERNAL_SERVICE_ERROR),
)


def install_error_handlers(http_application: FastAPI) -> None:
    """Register the ApplicationError -> HTTP status mapping on an app."""

    http_application.add_exception_handler(ApplicationError, handle_application_error)


async def handle_application_error(request: Request, error: Exception) -> JSONResponse:
    del request
    status_code: int = 500
    error_code: ApiErrorCode = ApiErrorCode.INTERNAL_ERROR
    for error_type, mapped_status_code, mapped_error_code in ERROR_STATUS_CODES:
        if isinstance(error, error_type):
            status_code = mapped_status_code
            error_code = mapped_error_code
            break

    headers: dict[str, str] = {}
    if status_code == 401:
        headers["WWW-Authenticate"] = "Bearer"

    body = ErrorBody(
        error=error_code,
        message=ErrorMessageText(str(error)),
        reasons=(
            list(error.reasons)
            if isinstance(error, ApplicationError) and error.reasons
            else None
        ),
    )
    return JSONResponse(
        status_code=status_code,
        content=body.model_dump(mode="json", exclude_none=True),
        headers=headers,
    )
