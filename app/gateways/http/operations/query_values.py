"""
Path and query parameters of the operations routes as typed values.

They arrive as raw strings (the transport boundary): a malformed id in the
path is a missing entity, any other invalid value is a validation error.
"""

from collections.abc import Callable
from typing import Annotated

from fastapi import Query

from app.schemas.exceptions.application_errors import (
    NotFoundError,
    ValidationFailedError,
)

TRUE_QUERY_VALUES: frozenset[str] = frozenset({"1", "true", "yes", "on"})
FALSE_QUERY_VALUES: frozenset[str] = frozenset({"0", "false", "no", "off"})

type OptionalQuery = Annotated[str | None, Query()]


def parse_path_id[Value](
    raw_value: str,
    id_type: Callable[[str], Value],
    entity: str,
) -> Value:
    """A malformed id in the path is reported as a missing entity."""

    try:
        return id_type(raw_value)
    except (ValueError, TypeError) as error:
        raise NotFoundError(f"{entity} {raw_value} was not found.") from error


def parse_text[Value](
    raw_value: str,
    value_type: Callable[[str], Value],
    name: str,
) -> Value:
    try:
        return value_type(raw_value)
    except (ValueError, TypeError) as error:
        raise ValidationFailedError(f"Invalid {name}: {raw_value!r}.") from error


def parse_optional_text[Value](
    raw_value: str | None,
    value_type: Callable[[str], Value],
    name: str,
) -> Value | None:
    if raw_value is None or raw_value == "":
        return None

    return parse_text(raw_value, value_type, name)


def parse_optional_integer[Value](
    raw_value: str | None,
    value_type: Callable[[int], Value],
    name: str,
) -> Value | None:
    if raw_value is None or raw_value == "":
        return None

    try:
        return value_type(int(raw_value))
    except (ValueError, TypeError) as error:
        raise ValidationFailedError(f"Invalid {name}: {raw_value!r}.") from error


def parse_flag(raw_value: str | None, name: str) -> bool:
    return parse_optional_flag(raw_value, name) or False


def parse_optional_flag(raw_value: str | None, name: str) -> bool | None:
    """True, False, or None when the parameter is missing or empty."""

    if raw_value is None or raw_value == "":
        return None

    normalized: str = raw_value.strip().lower()
    if normalized in TRUE_QUERY_VALUES:
        return True

    if normalized in FALSE_QUERY_VALUES:
        return False

    raise ValidationFailedError(f"Invalid {name}: {raw_value!r} (use true or false).")
