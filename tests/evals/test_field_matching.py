"""Tool input fields against the values a dataset expects."""

import pytest

from app.schemas.constants.assistants import AssistantToolName
from app.schemas.typings.evaluations.strings import ExpectedToolFieldValue
from app.utilities.assembly.eval_field_matching import (
    are_same_phone,
    is_matching_value,
    read_tool_input,
)
from tests.evals.eval_builders import tool_call


@pytest.mark.parametrize(
    ("expected", "actual", "matches"),
    [
        ("null", None, True),
        ("Nino", None, False),
        ("true", True, True),
        ("false", True, False),
        ("2", 2, True),
        ("2", 2.0, True),
        ("two", 2, False),
        ("+995555100201", "+995 555 10 02 01", True),
        ("+995555100201", "0555100201", True),
        ("+995555100201", "555100202", False),
        ("Nino", "nino beridze", True),
        ("2026-10-08", "2026-10-09", False),
    ],
)
def test_values_match_as_numbers_phones_or_text(
    expected: str, actual: object, matches: bool
) -> None:
    assert is_matching_value(ExpectedToolFieldValue(expected), actual) is matches


def test_short_digit_runs_are_not_phone_numbers() -> None:
    assert not are_same_phone("123", "123")


def test_unreadable_inputs_read_as_empty() -> None:
    assert read_tool_input(tool_call(AssistantToolName.GET_PRICE, "{oops")) == {}
    assert read_tool_input(tool_call(AssistantToolName.GET_PRICE, "[1, 2]")) == {}
