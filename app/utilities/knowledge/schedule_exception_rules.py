"""Rules for schedule exceptions: holidays, closed days and special hours.

Dates are calendar dates in the business time zone, computed with zoneinfo
from the injected clock.
"""

from collections.abc import Sequence
from datetime import UTC, date, datetime
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from typed_time_provider import Microseconds

from app.schemas.constants.businesses import Weekday
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.domain.profiles import OpeningInterval
from app.schemas.domain.resources import ScheduleExceptionDocument
from app.schemas.dto.resources import (
    ScheduleExceptionInput,
    ScheduleExceptionView,
)
from app.schemas.exceptions.application_errors import (
    ConflictError,
    ValidationFailedError,
)
from app.schemas.typings.bookings.booleans import IsClosedAllDay
from app.schemas.typings.bookings.constrained_strings import LocalDate
from app.schemas.typings.bookings.strings import ScheduleExceptionNote
from app.utilities.knowledge.opening_hours import validate_opening_intervals

MAX_NOTE_LENGTH: int = 300
MICROSECONDS_PER_SECOND: int = 1_000_000


def business_today(business: BusinessDocument, now: Microseconds) -> date:
    """Today's calendar date in the business time zone."""

    try:
        time_zone: ZoneInfo = ZoneInfo(business.timezone)
    except (ZoneInfoNotFoundError, ValueError) as error:
        raise ValidationFailedError(
            f"The business time zone {business.timezone} is unknown."
        ) from error

    moment: datetime = datetime.fromtimestamp(
        now // MICROSECONDS_PER_SECOND,
        tz=UTC,
    )
    return moment.astimezone(time_zone).date()


def parse_local_date(local_date: LocalDate) -> date:
    """A calendar date; rejects dates that do not exist (2026-02-30)."""

    try:
        return date.fromisoformat(local_date)
    except ValueError as error:
        raise ValidationFailedError(f"{local_date} is not a calendar date.") from error


def build_schedule_exception(
    business: BusinessDocument,
    exception_input: ScheduleExceptionInput,
    existing_exceptions: Sequence[ScheduleExceptionDocument],
    now: Microseconds,
) -> ScheduleExceptionDocument:
    """
    A validated holiday or special-hours day.

    Raises:
        ValidationFailedError: the date does not exist or is already past in
            the business time zone; a closed day has special hours; an open day
            has none, or has hours on another weekday.
        ConflictError: the same day already has an exception for the same
            resource (or for the whole business).
    """

    day: date = parse_local_date(exception_input.date)
    if day < business_today(business, now):
        raise ValidationFailedError(
            f"{exception_input.date} is already past in {business.timezone}."
        )

    special_hours: list[OpeningInterval] = check_special_hours(
        day,
        exception_input.is_closed_all_day,
        exception_input.special_hours,
    )
    for existing in existing_exceptions:
        if (
            existing.date == exception_input.date
            and existing.resource_id == exception_input.resource_id
        ):
            raise ConflictError(
                f"{exception_input.date} already has a schedule exception; delete "
                "it first."
            )

    return ScheduleExceptionDocument(
        business_id=business.id,
        resource_id=exception_input.resource_id,
        date=exception_input.date,
        is_closed_all_day=exception_input.is_closed_all_day,
        special_hours=special_hours,
        note=check_note(exception_input.note),
        created_at=now,
        updated_at=now,
    )


def check_special_hours(
    day: date,
    is_closed_all_day: IsClosedAllDay,
    special_hours: Sequence[OpeningInterval],
) -> list[OpeningInterval]:
    if is_closed_all_day:
        if special_hours != []:
            raise ValidationFailedError("A closed day cannot have special hours.")

        return []

    if special_hours == []:
        raise ValidationFailedError(
            "A day that is not closed needs special hours; use is_closed_all_day "
            "for a closed day."
        )

    weekday: Weekday = Weekday(day.isoweekday())
    for interval in special_hours:
        if interval.weekday is not weekday:
            raise ValidationFailedError(
                f"Special hours of {day.isoformat()} must be on "
                f"{weekday.name.lower()}, not on {interval.weekday.name.lower()}."
            )

    return validate_opening_intervals(special_hours, subject="Special hours")


def check_note(note: ScheduleExceptionNote | None) -> ScheduleExceptionNote | None:
    """The note as written, or None when it is missing or blank."""

    if note is None or note.strip() == "":
        return None

    if len(note.strip()) > MAX_NOTE_LENGTH:
        raise ValidationFailedError(
            f"A note must be at most {MAX_NOTE_LENGTH} characters."
        )

    return note


def to_schedule_exception_view(
    exception: ScheduleExceptionDocument,
) -> ScheduleExceptionView:
    return ScheduleExceptionView(
        id=exception.id,
        business_id=exception.business_id,
        resource_id=exception.resource_id,
        date=exception.date,
        weekday=Weekday(parse_local_date(exception.date).isoweekday()),
        is_closed_all_day=exception.is_closed_all_day,
        special_hours=list(exception.special_hours),
        note=exception.note,
    )
