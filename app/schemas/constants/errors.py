from enum import StrEnum


class ApiErrorCode(StrEnum):
    """
    Broad kind of a failed API request, the "error" field of every error
    body (app/gateways/http/error_responses.py maps errors to HTTP status).
    """

    NOT_FOUND = "not_found"
    VALIDATION_FAILED = "validation_failed"
    CONFLICT = "conflict"
    AUTHENTICATION_REQUIRED = "authentication_required"
    ACCESS_DENIED = "access_denied"
    RATE_LIMITED = "rate_limited"
    EXTERNAL_SERVICE_ERROR = "external_service_error"
    INTERNAL_ERROR = "internal_error"
