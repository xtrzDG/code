from datetime import datetime
from zoneinfo import ZoneInfo

import pytest

from app.schemas.constants.businesses import Weekday
from app.schemas.domain.profiles import OpeningInterval
from app.schemas.domain.resources import ScheduleExceptionDocument
from app.schemas.typings.bookings.constrained_strings import LocalDate
from app.schemas.typings.bookings.prefixed_id import ResourceId
from app.schemas.typings.businesses.constrained_integers import (
    ClosingMinuteOfDay,
    OpeningMinuteOfDay,
)
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.utilities.conversations.farewells import is_farewell
from app.utilities.conversations.opening_hours import is_open_at

BUSINESS_ID = BusinessId()


def interval(weekday: Weekday, opens: str, closes: str) -> OpeningInterval:
    def minutes(clock: str) -> int:
        hours, minutes_part = clock.split(":")
        return int(hours) * 60 + int(minutes_part)

    return OpeningInterval(
        weekday=weekday,
        opens_at=OpeningMinuteOfDay(minutes(opens)),
        closes_at=ClosingMinuteOfDay(minutes(closes)),
    )


def at(day: int, hour: int, minute: int = 0) -> datetime:
    """A moment in October 2026 in Tbilisi (1 October is a Thursday)."""

    return datetime(2026, 10, day, hour, minute, tzinfo=ZoneInfo("Asia/Tbilisi"))


NIGHT_CLUB_HOURS: list[OpeningInterval] = [
    interval(Weekday.FRIDAY, "22:00", "04:00"),
    interval(Weekday.SATURDAY, "22:00", "04:00"),
]
CAFE_HOURS: list[OpeningInterval] = [
    interval(weekday, "09:00", "24:00") for weekday in Weekday
]


@pytest.mark.parametrize(
    ("moment", "expected"),
    [
        (at(2, 21, 59), False),
        (at(2, 22, 0), True),
        (at(3, 3, 59), True),
        (at(3, 4, 0), False),
        (at(4, 2, 0), True),
        (at(5, 2, 0), False),
    ],
)
def test_overnight_intervals_run_past_midnight(
    moment: datetime, expected: bool
) -> None:
    assert is_open_at(moment, NIGHT_CLUB_HOURS, []) is expected


def test_closing_at_midnight_and_unknown_hours() -> None:
    assert is_open_at(at(1, 23, 59), CAFE_HOURS, []) is True
    assert is_open_at(at(1, 8, 59), CAFE_HOURS, []) is False
    assert is_open_at(at(1, 12, 0), [], []) is None


def test_holidays_and_special_hours_replace_the_day() -> None:
    holiday = ScheduleExceptionDocument(
        business_id=BUSINESS_ID,
        date=LocalDate("2026-10-01"),
    )
    short_day = ScheduleExceptionDocument(
        business_id=BUSINESS_ID,
        date=LocalDate("2026-10-02"),
        is_closed_all_day=False,
        special_hours=[interval(Weekday.FRIDAY, "10:00", "14:00")],
    )
    one_room_closed = ScheduleExceptionDocument(
        business_id=BUSINESS_ID,
        resource_id=ResourceId(),
        date=LocalDate("2026-10-03"),
    )
    exceptions = [holiday, short_day, one_room_closed]

    assert is_open_at(at(1, 12, 0), CAFE_HOURS, exceptions) is False
    assert is_open_at(at(2, 12, 0), CAFE_HOURS, exceptions) is True
    assert is_open_at(at(2, 15, 0), CAFE_HOURS, exceptions) is False
    assert is_open_at(at(3, 15, 0), CAFE_HOURS, exceptions) is True


@pytest.mark.parametrize(
    "text",
    [
        "Bye!",
        "Thanks, goodbye.",
        "Спасибо, до свидания!",
        "Дякую, до побачення",
        "მადლობა, ნახვამდის",
        "Teşekkürler, hoşça kal",
        "תודה, להתראות",
        "شكرا، مع السلامة",
        "Շնորհակալություն, ցտեսություն",
        "Danke, auf Wiederhören",
        "Merci, au revoir",
        "Gracias, adiós",
        "Grazie, arrivederci",
        "Obrigado, tchau",
        "Dziękuję, do widzenia",
        "Рақмет, сау болыңыз",
        "谢谢，再见",
        "ありがとうございます、失礼します",
    ],
)
def test_farewells_are_recognized_in_many_languages(text: str) -> None:
    assert is_farewell(text) is True


@pytest.mark.parametrize(
    "text",
    [
        "",
        "Hello",
        "Can I book a table and then say goodbye to my friends on Friday evening there",
        "Bye-laws of the club?",
        "Покажите меню",
    ],
)
def test_other_messages_are_not_farewells(text: str) -> None:
    assert is_farewell(text) is False
