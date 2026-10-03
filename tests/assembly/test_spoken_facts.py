"""Fact texts as they are said on the phone."""

import pytest

from app.schemas.domain.assistants import BusinessFact
from app.schemas.typings.profiles.constrained_strings import FactKey
from app.schemas.typings.profiles.strings import FactLabel, FactValue
from app.utilities.assembly.spoken_facts import speak_facts, speak_text


def fact(key: str, label: str, value: str) -> BusinessFact:
    return BusinessFact(
        key=FactKey(key), label=FactLabel(label), value=FactValue(value)
    )


@pytest.mark.parametrize(
    ("text", "spoken"),
    [
        ("Price: 18.00 GEL", "Price: 18 Georgian laris"),
        ("Price: 1.00 GEL", "Price: 1 Georgian lari"),
        ("Price: 18.50 GEL", "Price: 18.50 Georgian laris"),
        ("1500 JPY per person", "1500 Japanese yen per person"),
        ("1.250 KWD", "1.250 Kuwaiti dinars"),
        ("Room 12 ABC", "Room 12 ABC"),
        ("Model X5 BMW", "Model X5 BMW"),
    ],
)
def test_prices_are_said_with_the_currency_name(text: str, spoken: str) -> None:
    assert speak_text(text) == spoken


@pytest.mark.parametrize(
    ("text", "spoken"),
    [
        ("09:00–13:00, 14:00–18:00", "from 9:00 to 13:00, from 14:00 to 18:00"),
        ("18:00–24:00", "from 18:00 to midnight"),
        ("00:00–24:00", "around the clock"),
        ("Check-in from 14:00", "Check-in from 14:00"),
        ("Breakfast at 08:30", "Breakfast at 8:30"),
        ("Closed", "Closed"),
    ],
)
def test_hours_are_said_as_spoken_times(text: str, spoken: str) -> None:
    assert speak_text(text) == spoken


@pytest.mark.parametrize(
    ("text", "spoken"),
    [
        ("Special day 2026-12-31", "Special day 31 December 2026"),
        ("2027-01-07", "7 January 2027"),
        ("Code 2026-13-01", "Code 2026-13-01"),
    ],
)
def test_dates_are_said_with_the_month_name(text: str, spoken: str) -> None:
    assert speak_text(text) == spoken


def test_links_inside_a_text_become_a_note() -> None:
    assert speak_text("See https://example.ge/menu or www.example.ge today") == (
        "See (a link, never read it aloud) or (a link, never read it aloud) today"
    )


def test_rows_that_are_only_a_link_are_named_instead() -> None:
    table = speak_facts(
        [
            fact("business_name", "Business name", "Sakhli"),
            fact("link_menu", "Menu link", "https://example.ge/menu"),
            fact("maps_link", "Location on the map", "https://maps.example.com/1"),
            fact("deposit", "Deposit", "50.00 GEL"),
        ]
    )

    assert table.rows == [
        ("Business name", "Sakhli"),
        ("Deposit", "50 Georgian laris"),
    ]
    assert table.link_labels == ["Menu link", "Location on the map"]
