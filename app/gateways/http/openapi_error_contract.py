"""
The error contract in the API description: every error is an `ErrorBody`.

Each router documents the error statuses its routes answer with
`standard_error_responses(...)`, so the cabinet's generated client types its
failures. The app's `openapi()` then drops FastAPI's own validation error
schemas (`HTTPValidationError`, `ValidationError`), which the API never
sends: the framework's refusals are `ErrorBody` too
(`app/gateways/http/error_responses.py`).

    router = APIRouter(tags=["knowledge"], responses=standard_error_responses())
"""

from collections.abc import Callable
from typing import Any, cast

from fastapi import FastAPI

from app.schemas.dto.errors import ErrorBody

type OpenApiDocument = dict[str, Any]
type ResponseDescriptions = dict[int | str, dict[str, Any]]

ERROR_STATUS_DESCRIPTIONS: dict[int, str] = {
    401: "Sign-in required: the bearer token is missing, invalid or expired.",
    403: (
        "Signed in, but not allowed: staff on an owner-only action, or a "
        "country or plan that does not allow it."
    ),
    404: (
        "Not found, or not visible to the caller: another business and its "
        "data are reported as not found."
    ),
    409: "Conflicts with the current state (stale revision, slot taken).",
    412: (
        "The If-Match precondition does not hold: the resource was saved "
        "after the ETag was read (`error` conflict, reason "
        "`precondition_failed` with the current revision)."
    ),
    422: (
        "The request is invalid: a missing or malformed parameter, header or "
        "body (`reasons` name the fields), or a broken business rule."
    ),
    429: "Too many requests; Retry-After, when present, says when to retry.",
    502: "A provider (model, messaging, payments, telephony) failed.",
}
CABINET_ERROR_STATUSES: tuple[int, ...] = (401, 403, 404, 409, 422, 429, 502)
FRAMEWORK_VALIDATION_SCHEMAS: tuple[str, ...] = (
    "HTTPValidationError",
    "ValidationError",
)
SCHEMA_REFERENCE_PREFIX: str = "#/components/schemas/"
ERROR_BODY_REFERENCE: str = f"{SCHEMA_REFERENCE_PREFIX}{ErrorBody.__name__}"
FRAMEWORK_SCHEMA_REFERENCES: set[str] = {
    f"{SCHEMA_REFERENCE_PREFIX}{name}" for name in FRAMEWORK_VALIDATION_SCHEMAS
}
JSON_MEDIA_TYPE: str = "application/json"


def standard_error_responses(*status_codes: int) -> ResponseDescriptions:
    """
    OpenAPI `responses` for error statuses, each an `ErrorBody`; without
    arguments the cabinet set: 401, 403, 404, 409, 422, 429 and 502.

    Raises:
        ValueError: a status without a standard description.
    """

    chosen: tuple[int, ...] = status_codes or CABINET_ERROR_STATUSES
    unknown: list[int] = [
        code for code in chosen if code not in ERROR_STATUS_DESCRIPTIONS
    ]
    if unknown:
        raise ValueError(f"No standard error description for {unknown}.")

    return {
        code: {"model": ErrorBody, "description": ERROR_STATUS_DESCRIPTIONS[code]}
        for code in chosen
    }


def install_error_contract_openapi(http_application: FastAPI) -> None:
    """Make the app's `openapi()` describe every error as an `ErrorBody`."""

    build_framework_document: Callable[[], OpenApiDocument] = http_application.openapi

    def openapi() -> OpenApiDocument:
        if http_application.openapi_schema is None:
            http_application.openapi_schema = describe_errors_as_error_body(
                build_framework_document()
            )

        return http_application.openapi_schema

    http_application.openapi = openapi  # type: ignore[method-assign]


def describe_errors_as_error_body(document: OpenApiDocument) -> OpenApiDocument:
    """
    Point every response that uses FastAPI's validation error schema at
    `ErrorBody` instead, and drop those schemas from the components. An
    `ErrorBody` response is always JSON, also on a route whose success is
    plain text (the error handlers answer JSON).
    """

    replaced: bool = False
    for operations in cast(
        dict[str, dict[str, Any]], document.get("paths", {})
    ).values():
        for operation in operations.values():
            if not isinstance(operation, dict):
                continue

            responses = cast(
                dict[str, dict[str, Any]],
                cast(dict[str, Any], operation).get("responses", {}),
            )
            for status_code, response in responses.items():
                if references_any_schema(response, FRAMEWORK_SCHEMA_REFERENCES):
                    responses[status_code] = error_body_response(int(status_code))
                    replaced = True
                elif references_any_schema(response, {ERROR_BODY_REFERENCE}):
                    response["content"] = error_body_response(0)["content"]

    schemas = cast(
        dict[str, Any],
        document.setdefault("components", {}).setdefault("schemas", {}),
    )
    for name in FRAMEWORK_VALIDATION_SCHEMAS:
        schemas.pop(name, None)
    if replaced and ErrorBody.__name__ not in schemas:
        schemas.update(error_body_schemas())

    return document


def references_any_schema(response: dict[str, Any], references: set[str]) -> bool:
    """Whether some media type of the response uses one of the schemas."""

    content = cast(dict[str, dict[str, Any]], response.get("content", {}))
    return any(
        cast(dict[str, Any], media.get("schema", {})).get("$ref") in references
        for media in content.values()
    )


def error_body_response(status_code: int) -> dict[str, Any]:
    return {
        "description": ERROR_STATUS_DESCRIPTIONS.get(status_code, "Error."),
        "content": {JSON_MEDIA_TYPE: {"schema": {"$ref": ERROR_BODY_REFERENCE}}},
    }


def error_body_schemas() -> dict[str, Any]:
    """`ErrorBody` and the schemas it refers to, for the components."""

    schema: dict[str, Any] = ErrorBody.model_json_schema(
        ref_template=SCHEMA_REFERENCE_PREFIX + "{model}",
        mode="serialization",
    )
    definitions = cast(dict[str, Any], schema.pop("$defs", {}))
    return {**definitions, ErrorBody.__name__: schema}
