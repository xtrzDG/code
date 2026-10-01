"""Turn raw transport input into typed DTOs and primitives.

Request DTOs are strict, so JSON bodies are validated in JSON mode
(`model_validate_json`): enum values arrive as strings there, which strict
Python-mode validation would reject. Every failure becomes an application
error that the gateway maps to an HTTP status.
"""

import re
from collections.abc import Callable
from typing import Any

from pydantic import BaseModel, ValidationError

from app.schemas.exceptions.application_errors import (
    NotFoundError,
    ValidationFailedError,
)
from app.schemas.typings.localization.constrained_strings import LanguageTag

MAX_REPORTED_ERRORS: int = 5
TRUE_TEXTS: frozenset[str] = frozenset({"true", "1", "yes"})
FALSE_TEXTS: frozenset[str] = frozenset({"false", "0", "no"})
# One Accept-Language item: a language range and an optional quality weight.
ACCEPT_LANGUAGE_ITEM_PATTERN: re.Pattern[str] = re.compile(
    r"^\s*(?P<tag>[A-Za-z]{2,3}(?:-[A-Za-z0-9]{2,8})*)"
    r"\s*(?:;\s*q\s*=\s*(?P<q>[0-9.]+))?\s*$"
)


def parse_json_body[Model: BaseModel](
    model_type: type[Model], raw_body: bytes
) -> Model:
    """
    Validate a JSON request body as `model_type`.

    Raises:
        ValidationFailedError: the body is empty, not JSON, or breaks the schema.
    """

    if raw_body.strip() == b"":
        raise ValidationFailedError("The request body must be a JSON object.")

    try:
        return model_type.model_validate_json(raw_body)
    except ValidationError as error:
        raise ValidationFailedError(describe_validation_error(error)) from error


def describe_validation_error(error: ValidationError) -> str:
    """A short, readable summary of the first schema errors."""

    descriptions: list[str] = []
    for error_details in error.errors(include_url=False)[:MAX_REPORTED_ERRORS]:
        location: str = ".".join(str(part) for part in error_details["loc"])
        descriptions.append(f"{location or 'body'}: {error_details['msg']}")

    return "Invalid request body: " + "; ".join(descriptions)


def parse_path_value[Value](
    value_type: Callable[[str], Value],
    raw_value: str,
    description: str,
) -> Value:
    """
    A path segment as a typed value; malformed ids are reported as not found.

    Raises:
        NotFoundError: the segment is not a valid value of `value_type`.
    """

    try:
        return value_type(raw_value)
    except (ValueError, TypeError) as error:
        raise NotFoundError(f"{description} {raw_value!r} was not found.") from error


def parse_query_value[Value](
    value_type: Callable[[str], Value],
    raw_value: str | None,
    parameter_name: str,
) -> Value | None:
    """
    An optional query parameter as a typed value (None when absent or blank).

    Raises:
        ValidationFailedError: the value is not valid for `value_type`.
    """

    if raw_value is None or raw_value.strip() == "":
        return None

    try:
        return value_type(raw_value.strip())
    except (ValueError, TypeError) as error:
        raise ValidationFailedError(
            f"Query parameter {parameter_name} has an invalid value {raw_value!r}."
        ) from error


def parse_boolean_text(raw_value: str) -> bool:
    """A query flag: true/false, 1/0 or yes/no in any letter case."""

    folded: str = raw_value.strip().casefold()
    if folded in TRUE_TEXTS:
        return True

    if folded in FALSE_TEXTS:
        return False

    raise ValueError(f"{raw_value!r} is not a boolean.")


def parse_language_parameter(raw_value: str | None) -> LanguageTag | None:
    """A BCP 47 tag from a query parameter, tolerant of letter case ("pt-br")."""

    if raw_value is None or raw_value.strip() == "":
        return None

    language_tag: LanguageTag | None = canonical_language_tag(raw_value.strip())
    if language_tag is None:
        raise ValidationFailedError(
            f"Query parameter language has an invalid value {raw_value!r}."
        )

    return language_tag


def negotiate_language(accept_language: str | None) -> LanguageTag | None:
    """The preferred valid language of an Accept-Language header, if any."""

    if accept_language is None:
        return None

    candidates: list[tuple[float, int, LanguageTag]] = []
    for position, raw_item in enumerate(accept_language.split(",")):
        match: re.Match[str] | None = ACCEPT_LANGUAGE_ITEM_PATTERN.match(raw_item)
        if match is None:
            continue

        quality: float = parse_quality(match.group("q"))
        language_tag: LanguageTag | None = canonical_language_tag(match.group("tag"))
        if language_tag is not None and quality > 0.0:
            candidates.append((-quality, position, language_tag))

    if candidates == []:
        return None

    return min(candidates)[2]


def parse_quality(raw_quality: str | None) -> float:
    if raw_quality is None:
        return 1.0

    try:
        return float(raw_quality)
    except ValueError:
        return 0.0


def canonical_language_tag(raw_tag: str) -> LanguageTag | None:
    """
    Normalize letter case of a language tag ("EN-us" -> "en-US").

    Returns None when the tag is not a language[-Script][-REGION] tag.
    """

    parts: list[str] = raw_tag.replace("_", "-").split("-")
    canonical_parts: list[str] = [parts[0].lower()]
    for part in parts[1:]:
        if len(part) == 4 and part.isalpha():
            canonical_parts.append(part.title())
        elif len(part) == 2 and part.isalpha():
            canonical_parts.append(part.upper())
        else:
            canonical_parts.append(part)

    try:
        return LanguageTag("-".join(canonical_parts))
    except ValueError:
        return None


def json_body_openapi(*model_types: type[BaseModel]) -> dict[str, Any]:
    """
    OpenAPI `requestBody` for a route that reads its body with parse_json_body.

    Several model types become a `oneOf`. Each schema carries its own `$id`,
    so its internal `$defs` references resolve inside it (JSON Schema
    2020-12, OpenAPI 3.1).
    """

    schemas: list[dict[str, Any]] = []
    for model_type in model_types:
        schema: dict[str, Any] = model_type.model_json_schema()
        schema["$id"] = f"urn:assistant-workshop:request:{model_type.__name__}"
        schemas.append(schema)

    body_schema: dict[str, Any] = (
        schemas[0] if len(schemas) == 1 else {"oneOf": schemas}
    )
    return {
        "requestBody": {
            "required": True,
            "content": {"application/json": {"schema": body_schema}},
        }
    }
