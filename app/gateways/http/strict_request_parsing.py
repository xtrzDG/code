"""Transport-boundary parsing of request bodies, path ids and client IPs.

This is the one JSON-body stack of the HTTP layer. Request DTOs are strict
pydantic models: enums and typed primitives are accepted from JSON text but
not from already-decoded Python values, which is what FastAPI's own body
validation would pass. Bodies are therefore read as raw JSON and validated
with `model_validate_json`; failures become ValidationFailedError (HTTP 422)
through the shared error handlers.
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
EMPTY_JSON_OBJECT: bytes = b"{}"
EMPTY_BODY_MESSAGE: str = "The request body must be a JSON object."


def build_json_body_dependency[Body: BaseModel](
    body_type: type[Body],
    *,
    optional: bool = False,
) -> JsonBodyDependency[Body]:
    """
    Build a FastAPI dependency that parses the JSON body into `body_type`.

    With `optional=True` an empty body means `{}` (every field of such a
    body has a default); describe it with `describe_json_body(...,
    optional=True)`.

    Usage:
        read_body = build_json_body_dependency(CreateBusinessRequest)

        @router.post(
            "/v1/businesses",
            openapi_extra=describe_json_body(CreateBusinessRequest),
        )
        def create(body: Annotated[CreateBusinessRequest, Depends(read_body)]): ...
    """

    async def read_json_body(request: Request) -> Body:
        return parse_json_body(body_type, await request.body(), optional=optional)

    return read_json_body


async def read_raw_request_body(request: Request) -> bytes:
    """
    The request body exactly as sent: for signed webhooks (signatures cover
    the raw bytes) and for routes whose body type depends on the path, which
    then validate it with `parse_json_body`.
    """

    return await request.body()


def parse_json_body[Body: BaseModel](
    body_type: type[Body],
    raw_body: bytes,
    *,
    optional: bool = False,
) -> Body:
    """
    Validate a raw JSON request body as `body_type` in JSON mode.

    Raises:
        ValidationFailedError: the body is empty (unless optional), not JSON,
            or breaks the schema.
    """

    if raw_body.strip() == b"":
        if not optional:
            raise ValidationFailedError(EMPTY_BODY_MESSAGE)

        raw_body = EMPTY_JSON_OBJECT

    try:
        return body_type.model_validate_json(raw_body)
    except ValidationError as error:
        raise ValidationFailedError(describe_validation_error(error)) from error


def describe_json_body(
    *body_types: type[BaseModel],
    optional: bool = False,
) -> dict[str, Any]:
    """
    OpenAPI `requestBody` for a route that reads its body through this
    module, with nested models inlined. Several body types (the body type
    depends on the path) become a `oneOf`.
    """

    if body_types == ():
        raise ValueError("describe_json_body needs at least one body type.")

    schemas: list[object] = [inline_model_schema(body_type) for body_type in body_types]
    return {
        "requestBody": {
            "required": not optional,
            "content": {
                "application/json": {
                    "schema": schemas[0] if len(schemas) == 1 else {"oneOf": schemas}
                }
            },
        }
    }


def inline_model_schema(body_type: type[BaseModel]) -> object:
    """The JSON schema of a model with its `$defs` inlined."""

    schema: dict[str, object] = body_type.model_json_schema()
    definitions: dict[str, object] = cast(
        dict[str, object],
        schema.pop("$defs", {}),
    )
    return inline_local_references(schema, definitions)


def inline_local_references(
    node: object,
    definitions: dict[str, object],
    expanding: tuple[str, ...] = (),
) -> object:
    """
    Replace "#/$defs/..." references with the definitions they point to.

    Raises:
        ValueError: a definition refers to itself (it cannot be inlined).
    """

    if isinstance(node, list):
        return [
            inline_local_references(item, definitions, expanding)
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
            key: inline_local_references(value, definitions, expanding)
            for key, value in mapping.items()
        }

    name: str = reference.removeprefix(LOCAL_DEFINITION_PREFIX)
    if name in expanding:
        raise ValueError(f"Request schema {name!r} refers to itself.")

    definition: object = inline_local_references(
        definitions[name],
        definitions,
        (*expanding, name),
    )
    siblings: dict[str, object] = {
        key: inline_local_references(value, definitions, expanding)
        for key, value in mapping.items()
        if key != "$ref"
    }
    if isinstance(definition, dict):
        return cast(dict[str, object], definition) | siblings

    return definition


def describe_validation_error(error: ValidationError) -> str:
    """Summarize field errors without echoing the submitted values."""

    descriptions: list[str] = []
    for detail in error.errors(include_url=False)[:MAX_REPORTED_VALIDATION_ERRORS]:
        location: str = ".".join(str(part) for part in detail["loc"]) or "body"
        descriptions.append(f"{location}: {detail['msg']}")

    return "Invalid request: " + "; ".join(descriptions)


def parse_path_identifier[Identifier: str](
    raw_identifier: str,
    identifier_type: Callable[[str], Identifier],
    entity_label: str,
) -> Identifier:
    """
    Convert a path segment to a typed id, key or enum member; malformed
    values are reported as not found (without echoing them).
    """

    try:
        return identifier_type(raw_identifier)
    except (ValueError, TypeError) as error:
        raise NotFoundError(f"{entity_label} was not found.") from error


def read_client_ip_address(request: Request) -> ClientIpAddress | None:
    """IP address of the caller as the server sees it (for the audit log)."""

    if request.client is None:
        return None

    return ClientIpAddress(request.client.host)
