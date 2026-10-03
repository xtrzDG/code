"""Placing bookings in free time (pure decisions): time slots and stays."""

from collections.abc import Sequence

from app.schemas.constants.bookings import BookingUnit
from app.schemas.domain.resources import ResourceDocument
from app.utilities.scheduling.availability import (
    busy_ranges,
    is_date_closed_for_stays,
    resource_day_ranges,
)
from app.utilities.scheduling.nights import (
    StayBounds,
    stay_bounds,
    stay_dates,
)
from app.utilities.scheduling.opening_hours import ranges_around
from app.utilities.scheduling.overlap import has_free_unit
from app.utilities.scheduling.placement import Placement
from app.utilities.scheduling.placement_errors import (
    FAILURE_CLOSED,
    FAILURE_TAKEN,
    FAILURE_TIME_REQUIRED,
    FAILURE_TOO_SOON,
    placement_error,
)
from app.utilities.scheduling.placement_request import PlacementRequest
from app.utilities.scheduling.resource_selection import resolve_duration_minutes
from app.utilities.scheduling.slots import TimeSlot, fit_slot, generate_slots

DEFAULT_NIGHT_COUNT: int = 1


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
        request.sandbox_conversation_id,
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
        request.sandbox_conversation_id,
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
        request.sandbox_conversation_id,
    )
    if not has_free_unit(busy, slot.starts_at, slot.ends_at, int(resource.unit_count)):
        return FAILURE_TAKEN

    return Placement(resource, slot.starts_at, slot.ends_at)
