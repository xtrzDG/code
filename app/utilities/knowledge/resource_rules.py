"""Rules for bookable resources and schedule exceptions.

Defaults come from the niche (a restaurant books tables by time slots, a
hotel books rooms by nights). Dates are calendar dates in the business time
zone, computed with zoneinfo from the injected clock.
"""

from collections.abc import Sequence
from datetime import UTC, date, datetime
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from typed_time_provider import Microseconds

from app.schemas.constants.bookings import BookingUnit, ResourceKind
from app.schemas.constants.businesses import Weekday
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.domain.profiles import OpeningInterval
from app.schemas.domain.resources import ResourceDocument, ScheduleExceptionDocument
from app.schemas.dto.niches import NicheTemplate
from app.schemas.dto.resources import (
    ResourceInput,
    ResourcePatch,
    ResourceView,
    ScheduleExceptionInput,
    ScheduleExceptionView,
)
from app.schemas.exceptions.application_errors import (
    ConflictError,
    ValidationFailedError,
)
from app.schemas.typings.bookings.booleans import IsClosedAllDay
from app.schemas.typings.bookings.constrained_integers import SlotDurationMinutes
from app.schemas.typings.bookings.constrained_strings import LocalDate
from app.schemas.typings.bookings.strings import ResourceName, ScheduleExceptionNote
from app.utilities.knowledge.opening_hours import validate_opening_intervals
from app.utilities.knowledge.search_text import fold_words

MAX_RESOURCE_NAME_LENGTH: int = 120
MAX_NOTE_LENGTH: int = 300
MICROSECONDS_PER_SECOND: int = 1_000_000
REQUIRED_RESOURCE_PATCH_FIELDS: tuple[str, ...] = (
    "kind",
    "name",
    "capacity",
    "unit_count",
    "booking_unit",
    "schedule",
    "is_active",
)


def build_resource(
    business: BusinessDocument,
    template: NicheTemplate,
    resource_input: ResourceInput,
    existing_resources: Sequence[ResourceDocument],
    now: Microseconds,
) -> ResourceDocument:
    """A validated new resource with niche defaults for kind and booking unit."""

    kind: ResourceKind = (
        resource_input.kind
        if resource_input.kind is not None
        else template.resource_kind
    )
    booking_unit: BookingUnit = (
        resource_input.booking_unit
        if resource_input.booking_unit is not None
        else template.booking_unit
    )
    return ResourceDocument(
        business_id=business.id,
        kind=kind,
        name=check_resource_name(resource_input.name, existing_resources),
        capacity=resource_input.capacity,
        unit_count=resource_input.unit_count,
        booking_unit=booking_unit,
        slot_minutes=check_slot_minutes(booking_unit, resource_input.slot_minutes),
        schedule=validate_opening_intervals(
            resource_input.schedule,
            subject="Resource schedule",
        ),
        is_active=resource_input.is_active,
        created_at=now,
        updated_at=now,
    )


def patch_resource(
    existing: ResourceDocument,
    patch: ResourcePatch,
    other_resources: Sequence[ResourceDocument],
    now: Microseconds,
) -> ResourceDocument:
    """
    A resource with the fields present in `patch` changed.

    Only `slot_minutes` can be cleared with null; an empty schedule returns
    the resource to the business hours.
    """

    provided: set[str] = patch.model_fields_set
    for required_field in REQUIRED_RESOURCE_PATCH_FIELDS:
        if required_field in provided and getattr(patch, required_field) is None:
            raise ValidationFailedError(f"Field {required_field} cannot be null.")

    booking_unit: BookingUnit = (
        existing.booking_unit if patch.booking_unit is None else patch.booking_unit
    )
    slot_minutes: SlotDurationMinutes | None = (
        patch.slot_minutes if "slot_minutes" in provided else existing.slot_minutes
    )
    if booking_unit is BookingUnit.NIGHT and "slot_minutes" not in provided:
        slot_minutes = None

    return ResourceDocument(
        id=existing.id,
        business_id=existing.business_id,
        kind=existing.kind if patch.kind is None else patch.kind,
        name=(
            existing.name
            if patch.name is None
            else check_resource_name(patch.name, other_resources)
        ),
        capacity=existing.capacity if patch.capacity is None else patch.capacity,
        unit_count=existing.unit_count
        if patch.unit_count is None
        else patch.unit_count,
        booking_unit=booking_unit,
        slot_minutes=check_slot_minutes(booking_unit, slot_minutes),
        schedule=(
            existing.schedule
            if patch.schedule is None
            else validate_opening_intervals(patch.schedule, subject="Resource schedule")
        ),
        is_active=existing.is_active if patch.is_active is None else patch.is_active,
        created_at=existing.created_at,
        updated_at=now,
    )


def check_resource_name(
    name: ResourceName,
    other_resources: Sequence[ResourceDocument],
) -> ResourceName:
    """
    The name as written, if no other resource of the business uses it
    (ignoring case, accents and spacing).
    """

    stripped_length: int = len(name.strip())
    if stripped_length == 0 or stripped_length > MAX_RESOURCE_NAME_LENGTH:
        raise ValidationFailedError(
            f"A resource needs a name of 1 to {MAX_RESOURCE_NAME_LENGTH} characters."
        )

    folded_name: str = fold_words(name)
    for resource in other_resources:
        if fold_words(resource.name) == folded_name:
            raise ConflictError(f"A resource named {name.strip()!r} already exists.")

    return name


def check_slot_minutes(
    booking_unit: BookingUnit,
    slot_minutes: SlotDurationMinutes | None,
) -> SlotDurationMinutes | None:
    """Night resources are booked by nights and have no slot length."""

    if booking_unit is BookingUnit.NIGHT and slot_minutes is not None:
        raise ValidationFailedError(
            "Resources booked by nights have no slot length; leave slot_minutes empty."
        )

    return slot_minutes


def to_resource_view(resource: ResourceDocument) -> ResourceView:
    return ResourceView(
        id=resource.id,
        business_id=resource.business_id,
        kind=resource.kind,
        name=resource.name,
        capacity=resource.capacity,
        unit_count=resource.unit_count,
        booking_unit=resource.booking_unit,
        slot_minutes=resource.slot_minutes,
        schedule=list(resource.schedule),
        is_active=resource.is_active,
        created_at=resource.created_at,
        updated_at=resource.updated_at,
    )


def resource_sort_key(resource: ResourceDocument) -> tuple[str, str, str]:
    return (resource.kind.value, fold_words(resource.name), str(resource.id))


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
