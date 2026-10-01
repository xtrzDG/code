"""Booking-aware building blocks shared by availability and booking writes."""

from collections.abc import Sequence
from datetime import date

from app.schemas.constants.bookings import BookingStatus, BookingUnit
from app.schemas.domain.bookings import BookingDocument
from app.schemas.domain.profiles import OpeningInterval
from app.schemas.domain.resources import ResourceDocument, ScheduleExceptionDocument
from app.schemas.typings.bookings.prefixed_id import BookingId
from app.utilities.scheduling.opening_hours import (
    DayRanges,
    MinuteRange,
    find_exception,
    is_open_on_date,
    resource_ranges_starting_on,
)
from app.utilities.scheduling.overlap import BusyRange

DEFAULT_SLOT_MINUTES: int = 60
BLOCKING_BOOKING_STATUSES: frozenset[BookingStatus] = frozenset(
    {BookingStatus.PENDING, BookingStatus.CONFIRMED}
)


def is_blocking(booking: BookingDocument, include_sandbox: bool) -> bool:
    """
    Whether a booking takes a unit. Real availability counts real bookings
    only; sandbox (owner test, autotests) counts real and sandbox ones, so
    tests never take real customers' slots but still see them.
    """

    if booking.status not in BLOCKING_BOOKING_STATUSES:
        return False

    return include_sandbox or not booking.is_sandbox


def busy_ranges(
    bookings: Sequence[BookingDocument],
    resource: ResourceDocument,
    include_sandbox: bool,
    excluded_booking_id: BookingId | None = None,
) -> list[BusyRange]:
    return [
        BusyRange(int(booking.starts_at), int(booking.ends_at))
        for booking in bookings
        if booking.resource_id == resource.id
        and booking.id != excluded_booking_id
        and is_blocking(booking, include_sandbox)
    ]


def resource_day_ranges(
    resource: ResourceDocument,
    business_hours: Sequence[OpeningInterval],
    exceptions: Sequence[ScheduleExceptionDocument],
) -> DayRanges:
    """Opening ranges of the resource starting on any given date."""

    resource_schedule: list[OpeningInterval] = list(resource.schedule)
    weekly_hours: list[OpeningInterval] = list(business_hours)
    exception_days: list[ScheduleExceptionDocument] = list(exceptions)

    def ranges_starting_on(local_date: date) -> list[MinuteRange]:
        return resource_ranges_starting_on(
            local_date,
            resource.id,
            resource_schedule,
            weekly_hours,
            exception_days,
        )

    return ranges_starting_on


def is_date_closed_for_stays(
    local_date: date,
    resource: ResourceDocument,
    exceptions: Sequence[ScheduleExceptionDocument],
) -> bool:
    """
    Nights ignore weekly hours (a hotel is open around the clock); only a
    closed-all-day exception closes a night. A resource-level exception for
    the date wins over the business-level one.
    """

    resource_exception: ScheduleExceptionDocument | None = find_exception(
        exceptions, local_date, resource.id
    )
    if resource_exception is not None:
        return resource_exception.is_closed_all_day

    business_exception: ScheduleExceptionDocument | None = find_exception(
        exceptions, local_date, None
    )
    return business_exception is not None and business_exception.is_closed_all_day


def is_resource_open_on(
    local_date: date,
    resource: ResourceDocument,
    business_hours: Sequence[OpeningInterval],
    exceptions: Sequence[ScheduleExceptionDocument],
) -> bool:
    if resource.booking_unit is BookingUnit.NIGHT:
        return not is_date_closed_for_stays(local_date, resource, exceptions)

    return is_open_on_date(
        local_date, resource_day_ranges(resource, business_hours, exceptions)
    )
