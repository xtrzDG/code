"""Transport-boundary parsing of request bodies, path ids and client IPs.

Request DTOs are strict pydantic models: enums and typed primitives are
accepted from JSON text but not from already-decoded Python values, which is
what FastAPI's own body validation would pass. Bodies are therefore read as
raw JSON and validated with `model_validate_json`; failures become
ValidationFailedError (HTTP 422) through the shared error handlers.
"""

from collections.abc import Callable, Coroutine
from typing import Any, cast

from fastapi import Request
from pydantic import BaseModel, ValidationError

from app.schemas.exceptions.application_errors import (
    NotFoundError,
    ValidationFailedError,
)
from app.schemas.typings.compliance.strings import ClientIpAddress

type JsonBodyDependency[Body: BaseModel] = Callable[
    [Request],
    Coroutine[Any, Any, Body],
]

MAX_REPORTED_VALIDATION_ERRORS: int = 5
LOCAL_DEFINITION_PREFIX: str = "#/$defs/"


def build_json_body_dependency[Body: BaseModel](
    body_type: type[Body],
) -> JsonBodyDependency[Body]:
    """
    Build a FastAPI dependency that parses the JSON body into `body_type`.

    Usage:
        read_body = build_json_body_dependency(CreateBusinessRequest)

        @router.post(
            "/v1/businesses",
            openapi_extra=describe_json_body(CreateBusinessRequest),
        )
        def create(body: Annotated[CreateBusinessRequest, Depends(read_body)]): ...
    """

    async def read_json_body(request: Request) -> Body:
        raw_body: bytes = await request.body()
        try:
            return body_type.model_validate_json(raw_body)
        except ValidationError as error:
            raise ValidationFailedError(describe_validation_error(error)) from error

    return read_json_body


def describe_json_body(body_type: type[BaseModel]) -> dict[str, Any]:
    """
    OpenAPI `requestBody` for a route that reads its body through
    `build_json_body_dependency`, with nested models inlined.
    """

    schema: dict[str, object] = body_type.model_json_schema()
    definitions: dict[str, object] = cast(
        dict[str, object],
        schema.pop("$defs", {}),
    )
    return {
        "requestBody": {
            "required": True,
            "content": {
                "application/json": {
                    "schema": inline_local_references(schema, definitions)
                }
            },
        }
    }


def inline_local_references(
    node: object,
    definitions: dict[str, object],
) -> object:
    """Replace "#/$defs/..." references with the definitions they point to."""

    if isinstance(node, list):
        return [
            inline_local_references(item, definitions)
            for item in cast(list[object], node)
        ]

    if not isinstance(node, dict):
        return node

    mapping: dict[str, object] = cast(dict[str, object], node)
    reference: object = mapping.get("$ref")
    if not (
        isinstance(reference, str) and reference.startswith(LOCAL_DEFINITION_PREFIX)
    ):
        return {
            key: inline_local_references(value, definitions)
            for key, value in mapping.items()
        }

    definition: object = inline_local_references(
        definitions[reference.removeprefix(LOCAL_DEFINITION_PREFIX)],
        definitions,
    )
    siblings: dict[str, object] = {
        key: inline_local_references(value, definitions)
        for key, value in mapping.items()
        if key != "$ref"
    }
    if isinstance(definition, dict):
        return cast(dict[str, object], definition) | siblings

    return definition


def describe_validation_error(error: ValidationError) -> str:
    """Summarize field errors without echoing the submitted values."""

    descriptions: list[str] = []
    for detail in error.errors()[:MAX_REPORTED_VALIDATION_ERRORS]:
        location: str = ".".join(str(part) for part in detail["loc"]) or "body"
        descriptions.append(f"{location}: {detail['msg']}")

    return "Invalid request: " + "; ".join(descriptions)


def parse_path_identifier[Identifier: str](
    raw_identifier: str,
    identifier_type: Callable[[str], Identifier],
    entity_label: str,
) -> Identifier:
    """Convert a path segment to a typed id; malformed ids are not found."""

    try:
        return identifier_type(raw_identifier)
    except (ValueError, TypeError) as error:
        raise NotFoundError(f"{entity_label} was not found.") from error


def read_client_ip_address(request: Request) -> ClientIpAddress | None:
    """IP address of the caller as the server sees it (for the audit log)."""

    if request.client is None:
        return None

    return ClientIpAddress(request.client.host)
