"""
Single place where errors become HTTP responses.

Every error body is an `ErrorBody`: {"error": "<code>", "message": "<English
text>"}. When the error carries machine-readable reasons
(`ApplicationError.reasons`), the body also has "reasons": [{"code",
"message", "details"}, ...], e.g. the failed go-live checks of a refused
publish (409) or why a menu link could not be read (422). The field is
absent otherwise, and clients that do not know it ignore it. A 429 whose
error knows how long to wait (`RateLimitedError.retry_after_seconds`) carries
a Retry-After header.

The framework's own refusals speak the same language: a missing or
malformed query parameter or header is a 422 `validation_failed` with one
reason per field (`missing` or `invalid`, the field's location as detail),
and an unknown route or method keeps its status with an `ErrorBody`.
"""

from collections.abc import Mapping, Sequence
from http import HTTPStatus
from typing import cast

from base_typed_string import BaseTypedStringConstraintViolationError
from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.gateways.http.openapi_error_contract import install_error_contract_openapi
from app.schemas.constants.errors import ApiErrorCode
from app.schemas.dto.errors import ErrorBody, ErrorReason
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
from app.schemas.typings.platform.constrained_strings import (
    ErrorReasonCode,
    ErrorReasonDetail,
)
from app.schemas.typings.platform.strings import ErrorMessageText, ErrorReasonMessage

ERROR_STATUS_CODES: tuple[tuple[type[ApplicationError], int, ApiErrorCode], ...] = (
    (NotFoundError, 404, ApiErrorCode.NOT_FOUND),
    (ValidationFailedError, 422, ApiErrorCode.VALIDATION_FAILED),
    (ConflictError, 409, ApiErrorCode.CONFLICT),
    (AuthenticationRequiredError, 401, ApiErrorCode.AUTHENTICATION_REQUIRED),
    (AccessDeniedError, 403, ApiErrorCode.ACCESS_DENIED),
    (RateLimitedError, 429, ApiErrorCode.RATE_LIMITED),
    (ExternalServiceError, 502, ApiErrorCode.EXTERNAL_SERVICE_ERROR),
)
# The error code of a framework refusal (no route, wrong method) by status;
# other 4xx statuses mean the request as sent cannot be processed.
HTTP_STATUS_ERROR_CODES: dict[int, ApiErrorCode] = {
    401: ApiErrorCode.AUTHENTICATION_REQUIRED,
    403: ApiErrorCode.ACCESS_DENIED,
    404: ApiErrorCode.NOT_FOUND,
    409: ApiErrorCode.CONFLICT,
    429: ApiErrorCode.RATE_LIMITED,
    502: ApiErrorCode.EXTERNAL_SERVICE_ERROR,
    503: ApiErrorCode.EXTERNAL_SERVICE_ERROR,
    504: ApiErrorCode.EXTERNAL_SERVICE_ERROR,
}
MAX_REPORTED_VALIDATION_ERRORS: int = 5
MISSING_FIELD_ERROR_TYPE: str = "missing"
MISSING_REASON_CODE: ErrorReasonCode = ErrorReasonCode("missing")
INVALID_REASON_CODE: ErrorReasonCode = ErrorReasonCode("invalid")
REQUEST_LOCATION: str = "request"


def install_error_handlers(http_application: FastAPI) -> None:
    """
    Register the error -> HTTP response mapping on an app, and describe it
    in the app's OpenAPI document (every error is an `ErrorBody`).
    """

    http_application.add_exception_handler(ApplicationError, handle_application_error)
    http_application.add_exception_handler(
        RequestValidationError,
        handle_request_validation_error,
    )
    http_application.add_exception_handler(
        StarletteHTTPException,
        handle_http_exception,
    )
    install_error_contract_openapi(http_application)


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
    if isinstance(error, RateLimitedError) and error.retry_after_seconds is not None:
        headers["Retry-After"] = str(int(error.retry_after_seconds))

    return error_response(
        status_code,
        ErrorBody(
            error=error_code,
            message=ErrorMessageText(str(error)),
            reasons=(
                list(error.reasons)
                if isinstance(error, ApplicationError) and error.reasons
                else None
            ),
        ),
        headers,
    )


async def handle_request_validation_error(
    request: Request,
    error: Exception,
) -> JSONResponse:
    """
    A query parameter, header or body field the framework itself refused:
    422 with one reason per field (without echoing the submitted values).
    """

    del request
    field_errors: Sequence[Mapping[str, object]] = (
        error.errors() if isinstance(error, RequestValidationError) else ()
    )
    reasons: list[ErrorReason] = [
        describe_field_error(field_error)
        for field_error in field_errors[:MAX_REPORTED_VALIDATION_ERRORS]
    ]
    summary: str = "; ".join(
        f"{location_of(reason)}: {reason.message}" for reason in reasons
    )
    return error_response(
        422,
        ErrorBody(
            error=ApiErrorCode.VALIDATION_FAILED,
            message=ErrorMessageText(
                f"Invalid request: {summary}" if summary else "Invalid request."
            ),
            reasons=reasons or None,
        ),
        {},
    )


async def handle_http_exception(request: Request, error: Exception) -> JSONResponse:
    """An unknown route, a wrong method or another framework refusal."""

    del request
    status_code: int = (
        error.status_code if isinstance(error, StarletteHTTPException) else 500
    )
    detail: object = getattr(error, "detail", None)
    headers: dict[str, str] = dict(
        getattr(error, "headers", None) or {},
    )
    return error_response(
        status_code,
        ErrorBody(
            error=error_code_for_status(status_code),
            message=ErrorMessageText(
                detail if isinstance(detail, str) else HTTPStatus(status_code).phrase
            ),
        ),
        headers,
    )


def error_response(
    status_code: int,
    body: ErrorBody,
    headers: dict[str, str],
) -> JSONResponse:
    if status_code == 401:
        headers = {**headers, "WWW-Authenticate": "Bearer"}

    return JSONResponse(
        status_code=status_code,
        content=body.model_dump(mode="json", exclude_none=True),
        headers=headers,
    )


def error_code_for_status(status_code: int) -> ApiErrorCode:
    mapped: ApiErrorCode | None = HTTP_STATUS_ERROR_CODES.get(status_code)
    if mapped is not None:
        return mapped

    if status_code >= 500:
        return ApiErrorCode.INTERNAL_ERROR

    return ApiErrorCode.VALIDATION_FAILED


def describe_field_error(field_error: Mapping[str, object]) -> ErrorReason:
    """One refused field as a reason: `missing` or `invalid`, its location."""

    location_parts: object = field_error.get("loc", ())
    location: str = (
        ".".join(str(part) for part in cast(Sequence[object], location_parts))
        if isinstance(location_parts, list | tuple)
        else ""
    ) or REQUEST_LOCATION
    return ErrorReason(
        code=(
            MISSING_REASON_CODE
            if field_error.get("type") == MISSING_FIELD_ERROR_TYPE
            else INVALID_REASON_CODE
        ),
        message=ErrorReasonMessage(str(field_error.get("msg", "Invalid value."))),
        details=as_reason_details(location),
    )


def as_reason_details(location: str) -> list[ErrorReasonDetail]:
    """The location as a reason detail, or none if it is not a safe token."""

    try:
        return [ErrorReasonDetail(location)]
    except BaseTypedStringConstraintViolationError:
        return []


def location_of(reason: ErrorReason) -> str:
    return str(reason.details[0]) if reason.details else REQUEST_LOCATION
