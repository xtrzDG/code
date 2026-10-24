"""Staff undo the last status change they made to a booking."""

from typed_time_provider import Microseconds

from app.contracts.use_case_contract import UseCaseContract
from app.schemas.domain.bookings import BookingStatusChange
from app.schemas.dto.bookings import BookingView
from app.schemas.dto.growth.freed_places import FreedPlace
from app.schemas.dto.operations.bookings import RevertBookingStatusCommand
from app.use_cases.bookings.booking_status_transition import BookingStatusTransition
from app.use_cases.bookings.booking_support import SchedulingInputs, find_resource
from app.use_cases.bookings.freed_places import held_place_of
from app.use_cases.bookings.status_undo import (
    ensure_time_still_free,
    require_undoable,
    takes_time_again,
)


class RevertBookingStatusUseCase(
    UseCaseContract[RevertBookingStatusCommand, BookingView]
):
    """
    The Undo of a status change staff made in the cabinet (confirmed,
    completed, no-show, cancelled): the booking gets its previous status
    back, within UNDO_WINDOW_SECONDS of the change, once.

    The command names the status being undone, so an Undo never reverts a
    later change it did not see. A booking going back to PENDING or
    CONFIRMED from a status that freed its time takes its unit again: its
    time is checked under the business's booking lock the way the full-day
    availability counts it (staff rules, every booking not over on its
    date, itself excepted), and an Undo whose time someone took in the
    meantime is refused.

    Raises:
        NotFoundError: no such booking in the business.
        ConflictError: with the reason (nothing_to_undo, status_changed,
            undo_expired, slot_taken, place_gone).

    The change is audited with the staff member, the cabinets of the
    business hear of it, and the calendar event follows
    (BookingStatusTransition).
    """

    def __init__(self, transition: BookingStatusTransition) -> None:
        self._transition: BookingStatusTransition = transition

    def run(self, input_data: RevertBookingStatusCommand) -> BookingView:
        inputs: SchedulingInputs = self._transition.scheduling_inputs(
            input_data.business_id
        )
        now: Microseconds = self._transition.now()
        with self._transition.locked_booking(
            input_data.business_id, input_data.booking_id
        ) as booking:
            change: BookingStatusChange = require_undoable(
                booking, input_data.status, now
            )
            if takes_time_again(booking, change):
                ensure_time_still_free(
                    booking,
                    find_resource(inputs.resources, booking.resource_id),
                    self._transition.bookings_on_booked_date(booking, inputs, now),
                    inputs.blocked_times,
                )

            held_before: FreedPlace | None = held_place_of(booking)
            booking.status = change.previous_status
            booking.last_status_change = None
            self._transition.record(booking, input_data.actor_id, now)

        self._transition.announce(booking, held_before, now)
        return self._transition.view(
            booking, inputs, self._transition.contact_of(booking)
        )
