"""Choosing resources and placing bookings in free time (pure decisions).

Resources are tried best fit first (smallest capacity that seats the party,
then name), so a table for two is not given to a couple when a table for
eight is also free.
"""

from collections.abc import Sequence
from datetime import date
from typing import NamedTuple
from zoneinfo import ZoneInfo

from app.schemas.constants.bookings import (
    BookingRefusalCode,
    BookingUnit,
    ResourceKind,
)
from app.schemas.domain.bookings import BookingDocument
from app.schemas.domain.profiles import BookingRules, OpeningInterval
from app.schemas.domain.resources import ResourceDocument, ScheduleExceptionDocument
from app.schemas.dto.errors import ErrorReason
from app.schemas.exceptions.application_errors import (
    ConflictError,
    NotFoundError,
    ValidationFailedError,
)
from app.schemas.typings.bookings.constrained_integers import (
    BookingDurationMinutes,
    PartySize,
)
from app.schemas.typings.bookings.prefixed_id import BookingId, ResourceId
from app.schemas.typings.platform.constrained_strings import (
    ErrorReasonCode,
    ErrorReasonDetail,
)
from app.schemas.typings.platform.strings import ErrorReasonMessage
from app.utilities.scheduling.availability import (
    DEFAULT_SLOT_MINUTES,
    busy_ranges,
    is_date_closed_for_stays,
    resource_day_ranges,
)
from app.utilities.scheduling.nights import (
    StayBounds,
    StayTimes,
    stay_bounds,
    stay_dates,
)
from app.utilities.scheduling.opening_hours import ranges_around
from app.utilities.scheduling.overlap import has_free_unit
from app.utilities.scheduling.slots import TimeSlot, fit_slot, generate_slots
from app.utilities.scheduling.zoned_time import SECONDS_PER_MINUTE, to_local_date

DEFAULT_NIGHT_COUNT: int = 1
FAILURE_CLOSED: str = "closed"
FAILURE_TOO_SOON: str = "too_soon"
FAILURE_TAKEN: str = "taken"
FAILURE_TIME_REQUIRED: str = "time_required"


class Placement(NamedTuple):
    """Where and when a booking goes (UTC seconds)."""

    resource: ResourceDocument
    starts_at: int
    ends_at: int


class PlacementRequest(NamedTuple):
    """Everything needed to place one booking on a local date."""

    local_date: date
    minute_of_day: int | None
    duration_minutes: BookingDurationMinutes | None
    nights: int | None
    zone: ZoneInfo
    business_hours: Sequence[OpeningInterval]
    exceptions: Sequence[ScheduleExceptionDocument]
    bookings: Sequence[BookingDocument]
    rules: BookingRules | None
    stay_times: StayTimes
    earliest_start: int
    include_sandbox: bool
    excluded_booking_id: BookingId | None = None


def select_resources(
    resources: Sequence[ResourceDocument],
    resource_id: ResourceId | None,
    resource_kind: ResourceKind | None,
    rules: BookingRules | None,
) -> list[ResourceDocument]:
    """
    Active resources matching the request: one resource by id (NotFoundError
    when missing or inactive), else a kind (requested, else the profile's),
    else every active resource. A profile kind without resources falls back
    to every active resource.
    """

    active: list[ResourceDocument] = [
        resource for resource in resources if resource.is_active
    ]
    if resource_id is not None:
        matching: list[ResourceDocument] = [
            resource for resource in active if resource.id == resource_id
        ]
        if not matching:
            raise NotFoundError(f"Resource {resource_id} was not found.")

        return matching

    if resource_kind is not None:
        return [resource for resource in active if resource.kind is resource_kind]

    if rules is not None:
        of_profile_kind: list[ResourceDocument] = [
            resource for resource in active if resource.kind is rules.resource_kind
        ]
        if of_profile_kind:
            return of_profile_kind

    return active


def seating_resources(
    resources: Sequence[ResourceDocument],
    party_size: PartySize | None,
) -> list[ResourceDocument]:
    """Resources that seat the party, best fit first."""

    fitting: list[ResourceDocument] = [
        resource
        for resource in resources
        if party_size is None or int(resource.capacity) >= int(party_size)
    ]
    return sorted(fitting, key=lambda resource: (int(resource.capacity), resource.name))


def ensure_party_size_allowed(
    party_size: PartySize, rules: BookingRules | None
) -> None:
    """Online bookings are limited to the profile's maximum party size."""

    if rules is not None and int(party_size) > int(rules.max_party_size):
        message: str = (
            f"Online booking is limited to {int(rules.max_party_size)} guests; "
            f"a party of {int(party_size)} is handled by a manager (create a lead "
            "or hand off)."
        )
        raise ValidationFailedError(
            message,
            reasons=[
                booking_refusal_reason(
                    BookingRefusalCode.PARTY_TOO_LARGE,
                    message,
                    [str(int(rules.max_party_size))],
                )
            ],
        )


def min_notice_seconds(rules: BookingRules | None) -> int:
    if rules is None:
        return 0

    return int(rules.min_notice_minutes) * SECONDS_PER_MINUTE


def resolve_duration_minutes(
    requested: BookingDurationMinutes | None,
    resource: ResourceDocument,
    rules: BookingRules | None,
) -> int:
    """Requested length, else the resource's slot, else the profile's slot."""

    if requested is not None:
        return int(requested)

    if resource.slot_minutes is not None:
        return int(resource.slot_minutes)

    if rules is not None:
        return int(rules.slot_minutes)

    return DEFAULT_SLOT_MINUTES


def free_time_slots(
    resource: ResourceDocument,
    request: PlacementRequest,
) -> list[TimeSlot]:
    """Free slots of a time-slot resource on the date, from the earliest start."""

    duration: int = resolve_duration_minutes(
        request.duration_minutes, resource, request.rules
    )
    day_ranges = ranges_around(
        request.local_date,
        resource_day_ranges(resource, request.business_hours, request.exceptions),
    )
    busy = busy_ranges(
        request.bookings,
        resource,
        request.include_sandbox,
        request.excluded_booking_id,
    )
    return [
        slot
        for slot in generate_slots(
            request.local_date, request.zone, day_ranges, duration
        )
        if slot.starts_at >= request.earliest_start
        and has_free_unit(busy, slot.starts_at, slot.ends_at, int(resource.unit_count))
    ]


def free_stay(
    resource: ResourceDocument, request: PlacementRequest
) -> Placement | None:
    """The stay when every night is open and a unit is free for all of it."""

    outcome: Placement | str = place_stay(resource, request)
    return outcome if isinstance(outcome, Placement) else None


def place_booking(
    candidates: Sequence[ResourceDocument],
    request: PlacementRequest,
) -> Placement:
    """
    First candidate (best fit) with a free unit at the requested time.

    Raises:
        ConflictError: the time is valid but every fitting unit is taken.
        ValidationFailedError: closed, outside opening hours, too soon,
            missing time for a time-slot resource, or a wall time skipped by
            a daylight-saving jump.
    """

    failures: set[str] = set()
    for resource in candidates:
        outcome: Placement | str = (
            place_stay(resource, request)
            if resource.booking_unit is BookingUnit.NIGHT
            else place_time_slot(resource, request)
        )
        if isinstance(outcome, Placement):
            return outcome

        failures.add(outcome)

    raise placement_error(failures, request.local_date)


def place_stay(
    resource: ResourceDocument, request: PlacementRequest
) -> Placement | str:
    nights: int = request.nights or DEFAULT_NIGHT_COUNT
    if any(
        is_date_closed_for_stays(night, resource, request.exceptions)
        for night in stay_dates(request.local_date, nights)
    ):
        return FAILURE_CLOSED

    bounds: StayBounds = stay_bounds(
        request.local_date, nights, request.stay_times, request.zone
    )
    if bounds.starts_at < request.earliest_start:
        return FAILURE_TOO_SOON

    busy = busy_ranges(
        request.bookings,
        resource,
        request.include_sandbox,
        request.excluded_booking_id,
    )
    if not has_free_unit(
        busy, bounds.starts_at, bounds.ends_at, int(resource.unit_count)
    ):
        return FAILURE_TAKEN

    return Placement(resource, bounds.starts_at, bounds.ends_at)


def place_time_slot(
    resource: ResourceDocument,
    request: PlacementRequest,
) -> Placement | str:
    if request.minute_of_day is None:
        return FAILURE_TIME_REQUIRED

    duration: int = resolve_duration_minutes(
        request.duration_minutes, resource, request.rules
    )
    day_ranges = ranges_around(
        request.local_date,
        resource_day_ranges(resource, request.business_hours, request.exceptions),
    )
    slot: TimeSlot | None = fit_slot(
        request.local_date, request.minute_of_day, request.zone, day_ranges, duration
    )
    if slot is None:
        return FAILURE_CLOSED

    if slot.starts_at < request.earliest_start:
        return FAILURE_TOO_SOON

    busy = busy_ranges(
        request.bookings,
        resource,
        request.include_sandbox,
        request.excluded_booking_id,
    )
    if not has_free_unit(busy, slot.starts_at, slot.ends_at, int(resource.unit_count)):
        return FAILURE_TAKEN

    return Placement(resource, slot.starts_at, slot.ends_at)


def booking_refusal_reason(
    code: BookingRefusalCode,
    message: str,
    details: Sequence[str] = (),
) -> ErrorReason:
    """The machine-readable reason of a booking refusal (with its English text)."""

    return ErrorReason(
        code=ErrorReasonCode(code.value),
        message=ErrorReasonMessage(message),
        details=[ErrorReasonDetail(detail) for detail in details],
    )


def placement_error(failures: set[str], local_date: date) -> Exception:
    """
    The most useful error for the caller: taken, too soon, no time, closed.
    Each carries a reason code (with the day where it matters), so the
    cabinet can explain it in the user's language.
    """

    day: str = str(to_local_date(local_date))
    message: str
    if FAILURE_TAKEN in failures:
        message = (
            f"That time on {day} is already booked. Check availability for "
            "another time."
        )
        return ConflictError(
            message,
            reasons=[booking_refusal_reason(BookingRefusalCode.TAKEN, message, [day])],
        )

    if FAILURE_TOO_SOON in failures:
        message = "That time is too soon: bookings need more advance notice."
        return ValidationFailedError(
            message,
            reasons=[booking_refusal_reason(BookingRefusalCode.TOO_SOON, message)],
        )

    if FAILURE_TIME_REQUIRED in failures:
        message = "A time is required for this booking."
        return ValidationFailedError(
            message,
            reasons=[booking_refusal_reason(BookingRefusalCode.TIME_REQUIRED, message)],
        )

    if failures:
        message = (
            f"The business is closed at that time on {day} (outside opening hours "
            "or a holiday)."
        )
        return ValidationFailedError(
            message,
            reasons=[booking_refusal_reason(BookingRefusalCode.CLOSED, message, [day])],
        )

    message = "No bookable resource seats a party of this size."
    return ValidationFailedError(
        message,
        reasons=[
            booking_refusal_reason(BookingRefusalCode.NO_SEATING_RESOURCE, message)
        ],
    )
