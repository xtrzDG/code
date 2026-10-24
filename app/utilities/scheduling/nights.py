"""Stays booked by the night (hotels, rentals): nights, check-in and check-out.

Check-in and check-out times come from the profile's niche answers
(`check_in_time`, `check_out_time` written as "HH:MM"); without them the
international defaults 14:00 and 12:00 apply.
"""

import re
from datetime import date, timedelta
from typing import NamedTuple
from zoneinfo import ZoneInfo

from app.schemas.domain.profiles import BusinessProfileDocument
from app.utilities.scheduling.zoned_time import lenient_utc_seconds

DEFAULT_CHECK_IN_MINUTE: int = 14 * 60
DEFAULT_CHECK_OUT_MINUTE: int = 12 * 60
CHECK_IN_QUESTION_KEYS: frozenset[str] = frozenset({"check_in_time", "checkin_time"})
CHECK_OUT_QUESTION_KEYS: frozenset[str] = frozenset({"check_out_time", "checkout_time"})
TIME_IN_TEXT_PATTERN: re.Pattern[str] = re.compile(
    r"\b([01]?[0-9]|2[0-3])[:.]([0-5][0-9])\b"
)


class StayTimes(NamedTuple):
    """Check-in and check-out wall minutes of a business."""

    check_in_minute: int
    check_out_minute: int


class StayBounds(NamedTuple):
    """UTC seconds of check-in and check-out of one stay."""

    starts_at: int
    ends_at: int


def read_stay_times(profile: BusinessProfileDocument | None) -> StayTimes:
    check_in_minute: int = DEFAULT_CHECK_IN_MINUTE
    check_out_minute: int = DEFAULT_CHECK_OUT_MINUTE
    if profile is None:
        return StayTimes(check_in_minute, check_out_minute)

    for answer in profile.niche_answers:
        minute: int | None = find_time_in_text(str(answer.answer))
        if minute is None:
            continue

        if str(answer.question_key) in CHECK_IN_QUESTION_KEYS:
            check_in_minute = minute
        elif str(answer.question_key) in CHECK_OUT_QUESTION_KEYS:
            check_out_minute = minute

    return StayTimes(check_in_minute, check_out_minute)


def find_time_in_text(text: str) -> int | None:
    """Minute of the day of the first "H:MM" / "HH.MM" time in a text."""

    match: re.Match[str] | None = TIME_IN_TEXT_PATTERN.search(text)
    if match is None:
        return None

    return int(match.group(1)) * 60 + int(match.group(2))


def stay_dates(check_in: date, nights: int) -> list[date]:
    """The dates whose nights the stay covers (check-in date first)."""

    return [check_in + timedelta(days=offset) for offset in range(nights)]


def stay_bounds(
    check_in: date,
    nights: int,
    stay_times: StayTimes,
    zone: ZoneInfo,
) -> StayBounds:
    check_out: date = check_in + timedelta(days=nights)
    return StayBounds(
        starts_at=lenient_utc_seconds(check_in, stay_times.check_in_minute, zone),
        ends_at=lenient_utc_seconds(check_out, stay_times.check_out_minute, zone),
    )
