"""
A card number read out over several turns of a call: the pieces are
masked in each caller line; numbers that only sit next to each other stay.
"""

import pytest

from app.utilities.privacy.sensitive_numbers import (
    CARD_PLACEHOLDER,
    mask_sensitive_numbers,
)
from app.utilities.privacy.split_card_numbers import mask_split_card_numbers


def test_a_card_read_in_two_turns_is_masked_in_both() -> None:
    lines = ["La mia carta è 4242 4242", "4242 4242."]

    assert mask_split_card_numbers(lines) == [
        f"La mia carta è {CARD_PLACEHOLDER}",
        f"{CARD_PLACEHOLDER}.",
    ]


def test_a_card_read_a_group_at_a_time_is_masked_in_every_turn() -> None:
    lines = ["4242", "4242,", " 4242", "4242 grazie"]

    assert mask_split_card_numbers(lines) == [
        CARD_PLACEHOLDER,
        f"{CARD_PLACEHOLDER},",
        f" {CARD_PLACEHOLDER}",
        f"{CARD_PLACEHOLDER} grazie",
    ]


@pytest.mark.parametrize(
    "lines",
    [
        ["My number is 347 123 4567", "for 4 people", "at 19:30"],
        ["+39 347 123 4567", "4242 4242 4242"],
        ["Il codice è 12345", "67890"],
        ["Order 4242 4242", "4242 4241"],
        ["A table for 4", "2 adults and 2 children", "2026"],
    ],
)
def test_numbers_that_only_follow_each_other_stay(lines: list[str]) -> None:
    assert mask_split_card_numbers(lines) == lines


def test_a_card_masked_in_its_own_line_is_left_as_it_is() -> None:
    lines = [mask_sensitive_numbers("4242 4242 4242 4242"), "123"]

    assert mask_split_card_numbers(lines) == [CARD_PLACEHOLDER, "123"]
