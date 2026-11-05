"""Conversions between business-local wall time (IANA zone) and UTC seconds.

Wall times are a local date plus a minute offset from its midnight; offsets
may be negative or pass 1440 (previous or next day). Storage is UTC.
"""

from datetime import UTC, date, datetime, time, timedelta
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from app.schemas.constants.businesses import Weekday
from app.schemas.exceptions.application_errors import ValidationFailedError
from app.schemas.typings.bookings.constrained_strings import LocalDate, LocalTimeOfDay
from app.schemas.typings.localization.constrained_strings import TimezoneName

MINUTES_PER_DAY: int = 24 * 60
SECONDS_PER_MINUTE: int = 60
MICROSECONDS_PER_SECOND: int = 1_000_000
UNIX_EPOCH: datetime = datetime(1970, 1, 1, tzinfo=UTC)
ONE_SECOND: timedelta = timedelta(seconds=1)


def load_time_zone(timezone: TimezoneName) -> ZoneInfo:
    """IANA zone of a business; ValidationFailedError when it is unknown."""

    try:
        return ZoneInfo(str(timezone))
    except (ZoneInfoNotFoundError, ValueError, OSError) as error:
        raise ValidationFailedError(f"Unknown time zone {timezone!r}.") from error


def parse_local_date(local_date: LocalDate) -> date:
    """Calendar date; ValidationFailedError for impossible dates (Feb 30)."""

    try:
        return date.fromisoformat(str(local_date))
    except ValueError as error:
        raise ValidationFailedError(f"{local_date} is not a calendar date.") from error


def to_local_date(value: date) -> LocalDate:
    return LocalDate(value.isoformat())


def parse_time_of_day(local_time: LocalTimeOfDay) -> int:
    """Minute of the day of an "HH:MM" wall-clock time."""

    hours_text, minutes_text = str(local_time).split(":")
    return int(hours_text) * 60 + int(minutes_text)


def to_time_of_day(minute_offset: int) -> LocalTimeOfDay:
    """Wall-clock "HH:MM" of a minute offset (wraps around midnight)."""

    minute_of_day: int = minute_offset % MINUTES_PER_DAY
    return LocalTimeOfDay(f"{minute_of_day // 60:02d}:{minute_of_day % 60:02d}")


def iso_weekday(value: date) -> Weekday:
    return Weekday(value.isoweekday())


def minute_of_day(moment: datetime) -> int:
    return moment.hour * 60 + moment.minute


def wall_time(local_date: date, minute_offset: int) -> datetime:
    """Naive local wall time `minute_offset` minutes after the date's midnight."""

    return datetime.combine(local_date, time()) + timedelta(minutes=minute_offset)


def find_utc_seconds(
    local_date: date, minute_offset: int, zone: ZoneInfo
) -> int | None:
    """
    UTC seconds of a local wall time, or None when the wall time does not
    exist (skipped by a daylight-saving jump). Ambiguous wall times (clocks
    moved back) resolve to the first occurrence (fold=0).
    """

    naive_moment: datetime = wall_time(local_date, minute_offset)
    utc_moment: datetime = naive_moment.replace(tzinfo=zone, fold=0).astimezone(UTC)
    if utc_moment.astimezone(zone).replace(tzinfo=None) != naive_moment:
        return None

    return to_unix_seconds(utc_moment)


def require_utc_seconds(local_date: date, minute_offset: int, zone: ZoneInfo) -> int:
    """UTC seconds of a local wall time; ValidationFailedError when it is skipped."""

    utc_seconds: int | None = find_utc_seconds(local_date, minute_offset, zone)
    if utc_seconds is None:
        skipped: str = wall_time(local_date, minute_offset).strftime("%Y-%m-%d %H:%M")
        raise ValidationFailedError(
            f"{skipped} does not exist in {zone.key}: clocks move forward at that "
            "time. Choose another time."
        )

    return utc_seconds


def lenient_utc_seconds(local_date: date, minute_offset: int, zone: ZoneInfo) -> int:
    """
    UTC seconds of a local wall time that never fails: a skipped wall time maps
    to the instant just after the jump (used for opening-range bounds).
    """

    naive_moment: datetime = wall_time(local_date, minute_offset)
    return to_unix_seconds(naive_moment.replace(tzinfo=zone, fold=0))


def to_local_moment(utc_seconds: int, zone: ZoneInfo) -> datetime:
    """Aware local datetime of UTC seconds."""

    return (UNIX_EPOCH + timedelta(seconds=utc_seconds)).astimezone(zone)


def to_unix_seconds(moment: datetime) -> int:
    return (moment.astimezone(UTC) - UNIX_EPOCH) // ONE_SECOND


def microseconds_to_seconds(unix_microseconds: int) -> int:
    return unix_microseconds // MICROSECONDS_PER_SECOND


def local_day_start_microseconds(local_date: date, zone: ZoneInfo) -> int:
    """UTC microseconds of the first instant of a local date."""

    return lenient_utc_seconds(local_date, 0, zone) * MICROSECONDS_PER_SECOND
