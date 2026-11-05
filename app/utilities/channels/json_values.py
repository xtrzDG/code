"""Defensive reading of provider JSON (the external boundary).

Webhook bodies are parsed into plain Python values and read field by field;
a missing or mistyped field reads as None instead of raising, so one odd
event never breaks a whole delivery.
"""

import json
from typing import cast

type JsonObject = dict[str, object]


def parse_json_object(body: bytes | str) -> JsonObject | None:
    """The JSON object in `body`; None for invalid JSON or a non-object."""

    try:
        value: object = json.loads(body)
    except ValueError, UnicodeDecodeError:
        return None

    return as_object(value)


def as_object(value: object) -> JsonObject | None:
    if not isinstance(value, dict):
        return None

    mapping: dict[object, object] = cast(dict[object, object], value)
    if not all(isinstance(key, str) for key in mapping):
        return None

    return cast(JsonObject, mapping)


def read_object(source: JsonObject, key: str) -> JsonObject | None:
    return as_object(source.get(key))


def read_objects(source: JsonObject, key: str) -> list[JsonObject]:
    """The objects of a list field; other items are skipped."""

    value: object = source.get(key)
    if not isinstance(value, list):
        return []

    objects: list[JsonObject] = []
    for item in cast(list[object], value):
        item_object: JsonObject | None = as_object(item)
        if item_object is not None:
            objects.append(item_object)

    return objects


def read_strings(source: JsonObject, key: str) -> list[str]:
    """The strings of a list field; other items are skipped."""

    value: object = source.get(key)
    if not isinstance(value, list):
        return []

    return [item for item in cast(list[object], value) if isinstance(item, str)]


def read_text(source: JsonObject, key: str) -> str | None:
    """A string field, or None when missing, not a string or blank."""

    value: object = source.get(key)
    if not isinstance(value, str) or value.strip() == "":
        return None

    return value


def read_identifier(source: JsonObject, key: str) -> str | None:
    """
    An id that platforms send as a string or a number (Telegram chat ids,
    Meta ids); None when missing or of another type.
    """

    value: object = source.get(key)
    if isinstance(value, bool):
        return None

    if isinstance(value, int):
        return str(value)

    if isinstance(value, str) and value.strip() != "":
        return value.strip()

    return None


def read_integer(source: JsonObject, key: str) -> int | None:
    """An integer field (booleans are not integers here)."""

    value: object = source.get(key)
    if isinstance(value, bool) or not isinstance(value, int):
        return None

    return value


def read_number(source: JsonObject, key: str) -> float | None:
    """A finite number field, integer or float."""

    value: object = source.get(key)
    if isinstance(value, bool) or not isinstance(value, int | float):
        return None

    number: float = float(value)
    if number != number or number in (float("inf"), float("-inf")):
        return None

    return number


def read_flag(source: JsonObject, key: str) -> bool:
    """True only for a JSON true."""

    return source.get(key) is True
