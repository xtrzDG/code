"""
The free slots and stays of an availability query, from its candidate
resources (the steps of `CheckAvailabilityUseCase`).
"""

from collections.abc import Sequence
from datetime import date
from typing import NamedTuple

from app.schemas.constants.bookings import BookingUnit
from app.schemas.domain.knowledge import KnowledgeItemDocument
from app.schemas.domain.resources import ResourceDocument
from app.schemas.dto.bookings import AvailabilityQuery, AvailableSlot
from app.schemas.typings.bookings.booleans import IsOpenOnDate
from app.schemas.typings.bookings.constrained_integers import (
    BookingDurationMinutes,
    NightCount,
)
from app.schemas.typings.localization.constrained_strings import CurrencyCode
from app.use_cases.bookings.booking_support import SchedulingInputs
from app.utilities.bookings.booking_values import offer_of_booking
from app.utilities.bookings.stay_quotes import quote_stay
from app.utilities.scheduling.availability import is_resource_open_on
from app.utilities.scheduling.booking_placement import (
    DEFAULT_NIGHT_COUNT,
    free_stay,
    free_time_slots,
)
from app.utilities.scheduling.opening_hours import business_day_ranges, is_open_on_date
from app.utilities.scheduling.placement import Placement
from app.utilities.scheduling.placement_request import PlacementRequest
from app.utilities.scheduling.resource_selection import resolve_duration_minutes
from app.utilities.scheduling.slots import nearest_minutes
from app.utilities.scheduling.zoned_time import parse_time_of_day, to_time_of_day

NEAREST_SLOT_LIMIT: int = 5
FIRST_SLOT_LIMIT: int = 10
STAY_OPTION_LIMIT: int = 10


class StayPricing(NamedTuple):
    """What prices a free stay: the named offer, else each room's room type."""

    offer: KnowledgeItemDocument | None
    items: Sequence[KnowledgeItemDocument]
    currency_code: CurrencyCode


def time_slot(
    resource: ResourceDocument,
    request: PlacementRequest,
    query: AvailabilityQuery,
    minute_of_day: int,
) -> AvailableSlot:
    return AvailableSlot(
        resource_id=resource.id,
        resource_name=resource.name,
        booking_unit=BookingUnit.TIME_SLOT,
        date=query.date,
        time=to_time_of_day(minute_of_day),
        duration_minutes=BookingDurationMinutes(
            resolve_duration_minutes(request.duration_minutes, resource, request.rules)
        ),
    )


def nearest_time_slots(
    candidates: Sequence[ResourceDocument],
    request: PlacementRequest,
    query: AvailabilityQuery,
) -> list[AvailableSlot]:
    """
    The best-fitting resource for each free time: the five nearest to the
    requested time, else the first ten.
    """

    best_by_minute: dict[int, AvailableSlot] = {}
    for resource in candidates:
        if resource.booking_unit is not BookingUnit.TIME_SLOT:
            continue

        for slot in free_time_slots(resource, request):
            if slot.minute_of_day not in best_by_minute:
                best_by_minute[slot.minute_of_day] = time_slot(
                    resource, request, query, slot.minute_of_day
                )

    minutes: list[int] = sorted(best_by_minute)
    if query.time is not None:
        minutes = nearest_minutes(
            minutes, parse_time_of_day(query.time), NEAREST_SLOT_LIMIT
        )
    else:
        minutes = minutes[:FIRST_SLOT_LIMIT]

    return [best_by_minute[minute] for minute in minutes]


def all_time_slots(
    candidates: Sequence[ResourceDocument],
    request: PlacementRequest,
    query: AvailabilityQuery,
) -> list[AvailableSlot]:
    """Every free slot of every resource, by time, best fit first."""

    slots: list[tuple[int, int, AvailableSlot]] = []
    for rank, resource in enumerate(candidates):
        if resource.booking_unit is not BookingUnit.TIME_SLOT:
            continue

        slots.extend(
            (
                slot.minute_of_day,
                rank,
                time_slot(resource, request, query, slot.minute_of_day),
            )
            for slot in free_time_slots(resource, request)
        )

    return [slot for _, _, slot in sorted(slots, key=lambda item: item[:2])]


def free_stays(
    candidates: Sequence[ResourceDocument],
    request: PlacementRequest,
    query: AvailabilityQuery,
    pricing: StayPricing,
) -> list[AvailableSlot]:
    """Every resource free for the whole stay, with the stay's price when known."""

    nights: NightCount = NightCount(request.nights or DEFAULT_NIGHT_COUNT)
    stays: list[AvailableSlot] = []
    for resource in candidates:
        if resource.booking_unit is not BookingUnit.NIGHT:
            continue

        placement: Placement | None = free_stay(resource, request)
        if placement is None:
            continue

        offer: KnowledgeItemDocument | None = offer_of_booking(
            pricing.offer, resource, pricing.items
        )
        stays.append(
            AvailableSlot(
                resource_id=resource.id,
                resource_name=resource.name,
                booking_unit=BookingUnit.NIGHT,
                date=query.date,
                time=to_time_of_day(request.stay_times.check_in_minute),
                nights=nights,
                stay_quote=(
                    None
                    if offer is None
                    else quote_stay(
                        offer, request.local_date, nights, pricing.currency_code
                    )
                ),
            )
        )

    return stays if query.full_day else stays[:STAY_OPTION_LIMIT]


def is_open_for(
    local_date: date,
    matching: Sequence[ResourceDocument],
    inputs: SchedulingInputs,
) -> IsOpenOnDate:
    """Whether any matching resource (else the business) is open on the date."""

    if not matching:
        return is_open_on_date(
            local_date,
            business_day_ranges(inputs.business_hours, inputs.exceptions),
        )

    return any(
        is_resource_open_on(
            local_date, resource, inputs.business_hours, inputs.exceptions
        )
        for resource in matching
    )
