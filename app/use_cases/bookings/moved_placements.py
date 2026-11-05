"""
Placing a booking that moves or changes its resource: the new time of a
moved booking among its candidates, and the booked time on another
resource. Both respect every booking not over on the date and the
waitlist's held places (`bookings`), the booking itself excepted.
"""

from collections.abc import Sequence
from datetime import date, datetime

from app.schemas.constants.bookings import BookingUnit
from app.schemas.domain.bookings import BookingDocument
from app.schemas.domain.knowledge import KnowledgeItemDocument
from app.schemas.domain.resources import ResourceDocument
from app.schemas.exceptions.application_errors import ValidationFailedError
from app.schemas.typings.bookings.constrained_integers import BookingDurationMinutes
from app.schemas.typings.bookings.constrained_strings import LocalTimeOfDay
from app.schemas.typings.bookings.prefixed_id import ResourceId
from app.use_cases.bookings.booking_edits import booking_unit_label
from app.use_cases.bookings.booking_support import SchedulingInputs, stay_night_count
from app.use_cases.bookings.reschedule_candidates import (
    booked_length,
    reschedule_candidates,
)
from app.utilities.scheduling.booking_placement import place_booking
from app.utilities.scheduling.placement import Placement
from app.utilities.scheduling.placement_request import PlacementRequest
from app.utilities.scheduling.resource_selection import select_resources
from app.utilities.scheduling.zoned_time import (
    SECONDS_PER_MINUTE,
    minute_of_day,
    parse_time_of_day,
    to_local_moment,
)


def place_moved_booking(
    inputs: SchedulingInputs,
    booking: BookingDocument,
    current: ResourceDocument,
    offer: KnowledgeItemDocument | None,
    items: Sequence[KnowledgeItemDocument],
    new_date: date,
    new_time: LocalTimeOfDay | None,
    bookings: Sequence[BookingDocument],
    earliest_start: int,
    target: ResourceDocument | None = None,
) -> Placement:
    """
    The new time of a moved booking: same length (or nights), on `target`
    only when staff dropped it there, else its own resource first.
    """

    return place_booking(
        (
            [target]
            if target is not None
            else reschedule_candidates(inputs.resources, booking, current, offer, items)
        ),
        PlacementRequest(
            local_date=new_date,
            minute_of_day=None if new_time is None else parse_time_of_day(new_time),
            duration_minutes=booked_length(booking, current),
            nights=stay_night_count(booking, inputs.zone),
            zone=inputs.zone,
            business_hours=inputs.business_hours,
            exceptions=inputs.exceptions,
            bookings=bookings,
            rules=inputs.rules,
            stay_times=inputs.stay_times,
            earliest_start=earliest_start,
            include_sandbox=booking.is_sandbox,
            excluded_booking_id=booking.id,
            sandbox_conversation_id=booking.conversation_id,
            buffer_minutes=booking.buffer_minutes,
            blocked_times=inputs.blocked_times,
        ),
    )


def dropped_place(
    inputs: SchedulingInputs,
    booking: BookingDocument,
    current: ResourceDocument,
    resource_id: ResourceId | None,
) -> ResourceDocument | None:
    """
    The place staff dropped a booking on (the calendar), checked as an
    edit's new place is: active, booked the same way (time slots or
    nights) and seating the party; None without one.

    Raises:
        NotFoundError: no such active place.
        ValidationFailedError: it is booked another way, or too small.
    """

    if resource_id is None:
        return None

    target: ResourceDocument = select_resources(
        inputs.resources, resource_id, None, inputs.rules
    )[0]
    if target.booking_unit is not current.booking_unit:
        raise ValidationFailedError(
            f"{target.name} is booked by {booking_unit_label(target)}, unlike "
            f"{current.name}; make a new booking instead."
        )

    if int(target.capacity) < int(booking.party_size):
        raise ValidationFailedError(
            f"{target.name} seats at most {int(target.capacity)} guests, "
            f"not {int(booking.party_size)}."
        )

    return target


def ensure_free_at_booked_time(
    booking: BookingDocument,
    target: ResourceDocument,
    inputs: SchedulingInputs,
    bookings: Sequence[BookingDocument],
) -> None:
    """The target is open and has a free unit for the booked time (staff rules)."""

    starts: datetime = to_local_moment(int(booking.starts_at), inputs.zone)
    is_stay: bool = target.booking_unit is BookingUnit.NIGHT
    place_booking(
        [target],
        PlacementRequest(
            local_date=starts.date(),
            minute_of_day=None if is_stay else minute_of_day(starts),
            duration_minutes=(
                None
                if is_stay
                else BookingDurationMinutes(
                    (int(booking.ends_at) - int(booking.starts_at))
                    // SECONDS_PER_MINUTE
                )
            ),
            nights=stay_night_count(booking, inputs.zone) if is_stay else None,
            zone=inputs.zone,
            business_hours=inputs.business_hours,
            exceptions=inputs.exceptions,
            bookings=bookings,
            rules=inputs.rules,
            stay_times=inputs.stay_times,
            earliest_start=0,
            include_sandbox=booking.is_sandbox,
            excluded_booking_id=booking.id,
            sandbox_conversation_id=booking.conversation_id,
            buffer_minutes=booking.buffer_minutes,
            blocked_times=inputs.blocked_times,
        ),
    )
