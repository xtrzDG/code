from datetime import timedelta

import pytest
from typed_time_provider import Microseconds

from app.schemas.typings.localization.constrained_strings import TimezoneName
from app.schemas.typings.localization.strings import TimezoneDisplayName
from app.utilities.localization.timezones import (
    build_timezone_display_name,
    format_utc_offset,
    is_known_timezone_name,
    list_territory_timezone_names,
)
from tests.localization.builders import (
    JANUARY_2026_NANOSECONDS,
    JULY_2026_NANOSECONDS,
)

JULY_2026: Microseconds = Microseconds(JULY_2026_NANOSECONDS // 1000)
JANUARY_2026: Microseconds = Microseconds(JANUARY_2026_NANOSECONDS // 1000)


@pytest.mark.parametrize(
    ("timezone_name", "instant", "expected_display_name"),
    [
        ("Asia/Tbilisi", JULY_2026, "Asia/Tbilisi (UTC+04:00)"),
        ("Asia/Tbilisi", JANUARY_2026, "Asia/Tbilisi (UTC+04:00)"),
        ("Europe/Warsaw", JULY_2026, "Europe/Warsaw (UTC+02:00)"),
        ("Europe/Warsaw", JANUARY_2026, "Europe/Warsaw (UTC+01:00)"),
        ("America/New_York", JULY_2026, "America/New_York (UTC-04:00)"),
        ("America/New_York", JANUARY_2026, "America/New_York (UTC-05:00)"),
        ("America/St_Johns", JANUARY_2026, "America/St_Johns (UTC-03:30)"),
        ("Asia/Kathmandu", JULY_2026, "Asia/Kathmandu (UTC+05:45)"),
        ("Asia/Almaty", JULY_2026, "Asia/Almaty (UTC+05:00)"),
        ("Australia/Sydney", JULY_2026, "Australia/Sydney (UTC+10:00)"),
        ("Australia/Sydney", JANUARY_2026, "Australia/Sydney (UTC+11:00)"),
        ("UTC", JULY_2026, "UTC (UTC+00:00)"),
    ],
)
def test_display_name_shows_offset_in_force(
    timezone_name: str,
    instant: Microseconds,
    expected_display_name: str,
) -> None:
    display_name = build_timezone_display_name(TimezoneName(timezone_name), instant)

    assert display_name == expected_display_name
    assert type(display_name) is TimezoneDisplayName


def test_format_utc_offset_handles_signs_and_minutes() -> None:
    assert format_utc_offset(timedelta(hours=4)) == "+04:00"
    assert format_utc_offset(timedelta(hours=-3, minutes=-30)) == "-03:30"
    assert format_utc_offset(timedelta(hours=5, minutes=45)) == "+05:45"
    assert format_utc_offset(timedelta(0)) == "+00:00"
    assert format_utc_offset(timedelta(hours=-2, seconds=-30)) == "-02:00"


def test_territory_zones_come_from_cldr_and_exist_in_iana() -> None:
    georgia = list_territory_timezone_names("GE")
    usa = list_territory_timezone_names("US")

    assert georgia == [TimezoneName("Asia/Tbilisi")]
    assert TimezoneName("America/New_York") in usa
    assert TimezoneName("Pacific/Honolulu") in usa
    assert usa == sorted(usa)
    assert all(is_known_timezone_name(str(zone)) for zone in usa)
    assert list_territory_timezone_names("XK") == []
    assert list_territory_timezone_names("QQ") == []
