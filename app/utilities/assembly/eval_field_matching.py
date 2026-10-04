"""
Does a tool input field hold what the scenario expects?

The dataset writes expected values as text; the model writes JSON. A value
matches when it is the same number, the same phone number (digits compared,
a missing country code or trunk zero allowed) or contains the expected text
ignoring case and surrounding spaces ("Nino Beridze" holds "Nino").
"""

import json
from collections.abc import Mapping, Sequence
from typing import cast

from app.schemas.dto.conversation_feed.conversation_views import ToolCallView
from app.schemas.dto.evaluations import ExpectedToolCall
from app.schemas.typings.evaluations.strings import ExpectedToolFieldValue

MIN_PHONE_DIGITS: int = 7
NULL_TEXT: str = "null"


def read_tool_input(call: ToolCallView) -> dict[str, object]:
    """The call's input as an object; an unreadable input reads as empty."""

    try:
        parsed: object = json.loads(str(call.input_json))
    except json.JSONDecodeError:
        return {}

    return cast(dict[str, object], parsed) if isinstance(parsed, dict) else {}


def find_field_mismatches(
    expected: ExpectedToolCall,
    tool_input: Mapping[str, object],
) -> list[str]:
    """`field: wanted ... got ...` for every expected field the input misses."""

    mismatches: list[str] = []
    for field_name, values in expected.fields.items():
        actual: object = tool_input.get(str(field_name))
        if not any(is_matching_value(value, actual) for value in values):
            wanted: str = " or ".join(repr(str(value)) for value in values)
            mismatches.append(f"{field_name}: wanted {wanted}, got {actual!r}")

    return mismatches


def is_matching_value(expected: ExpectedToolFieldValue, actual: object) -> bool:
    """One expected text against one JSON value (see the module docstring)."""

    expected_text: str = str(expected).strip()
    if actual is None:
        return expected_text.casefold() == NULL_TEXT

    if isinstance(actual, bool):
        return expected_text.casefold() == str(actual).casefold()

    if isinstance(actual, int | float):
        try:
            return float(expected_text) == float(actual)
        except ValueError:
            return False

    actual_text: str = str(actual).strip()
    if is_phone_like(expected_text) and is_phone_like(actual_text):
        return are_same_phone(expected_text, actual_text)

    return expected_text.casefold() in actual_text.casefold()


def is_phone_like(text: str) -> bool:
    """Only digits, spaces, dashes, brackets and a leading plus, 7+ digits."""

    allowed: set[str] = set("0123456789+-() ")
    return set(text) <= allowed and len(only_digits(text)) >= MIN_PHONE_DIGITS


def are_same_phone(expected: str, actual: str) -> bool:
    """
    The same number with or without its country code or trunk zero:
    "+995 555 10 02 01", "555100201" and "0555100201" all match.
    """

    expected_digits: str = only_digits(expected).lstrip("0")
    actual_digits: str = only_digits(actual).lstrip("0")
    shorter, longer = sorted((expected_digits, actual_digits), key=len)
    return len(shorter) >= MIN_PHONE_DIGITS and longer.endswith(shorter)


def only_digits(text: str) -> str:
    return "".join(character for character in text if character.isdigit())


def find_matching_call(
    expected: ExpectedToolCall,
    calls: Sequence[ToolCallView],
) -> tuple[ToolCallView | None, list[str]]:
    """
    The first successful call of the tool whose input matches every
    expected field, or None with the mismatches of the closest such call
    (the one with the fewest).
    """

    best_mismatches: list[str] | None = None
    for call in calls:
        if call.tool_name is not expected.tool_name or call.is_error:
            continue

        mismatches: list[str] = find_field_mismatches(expected, read_tool_input(call))
        if not mismatches:
            return call, []

        if best_mismatches is None or len(mismatches) < len(best_mismatches):
            best_mismatches = mismatches

    if best_mismatches is None:
        return None, [f"{expected.tool_name} was not called successfully"]

    return None, best_mismatches
