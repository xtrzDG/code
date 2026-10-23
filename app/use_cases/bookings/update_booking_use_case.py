"""Staff change a booking in the cabinet."""

from typed_time_provider import Microseconds

from app.contracts.repositories.compliance_repositories import AuditLogRepoContract
from app.contracts.repositories.conversation_repositories import ContactRepoContract
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.domain.bookings import BookingDocument
from app.schemas.domain.contacts import ContactDocument
from app.schemas.domain.resources import ResourceDocument
from app.schemas.dto.bookings import BookingView
from app.schemas.dto.growth.freed_places import FreedPlace
from app.schemas.dto.operations.bookings import UpdateBookingCommand
from app.schemas.exceptions.application_errors import (
    ConflictError,
    NotFoundError,
    ValidationFailedError,
)
from app.schemas.typings.bookings.constrained_integers import PartySize
from app.use_cases.bookings.booking_edits import (
    apply_notes_change,
    apply_status_change,
    booking_unit_label,
)
from app.use_cases.bookings.booking_status_transition import BookingStatusTransition
from app.use_cases.bookings.booking_support import SchedulingInputs, find_resource
from app.use_cases.bookings.freed_places import held_place_of
from app.use_cases.bookings.moved_placements import ensure_free_at_booked_time
from app.use_cases.shared.operations_support import (
    ContactDetails,
    update_contact_details,
)
from app.utilities.scheduling.availability import BLOCKING_BOOKING_STATUSES
from app.utilities.scheduling.resource_selection import select_resources


class UpdateBookingUseCase(UseCaseContract[UpdateBookingCommand, BookingView]):
    """
    Staff change a booking in the cabinet; omitted fields stay as they are.

    - Status: COMPLETED, NO_SHOW or CANCELLED (from PENDING or CONFIRMED),
      or CONFIRMED for a PENDING booking. Setting the current status again
      is a no-op; other changes raise ConflictError. The staff member may
      undo the change for a short while (RevertBookingStatusUseCase).
    - Party size and resource, only while the booking is PENDING or
      CONFIRMED: the resource must be active, booked the same way (time
      slots or nights), seat the party, be open at the booked time and have
      a free unit then (the booking itself not counted). The online-booking
      limits (notice, maximum party) do not apply to staff, as for manual
      bookings. The time is changed by rescheduling.
    - Notes: an empty text removes them.
    - Contact name: renames the customer (audited as a contact change).

    Checks and writes run under the business lock. The booking change is
    audited once with the staff member, and the calendar event follows
    (BookingStatusTransition).
    """

    def __init__(
        self,
        transition: BookingStatusTransition,
        contact_repo: ContactRepoContract,
        audit_log_repo: AuditLogRepoContract,
    ) -> None:
        self._transition: BookingStatusTransition = transition
        self._contact_repo: ContactRepoContract = contact_repo
        self._audit_log_repo: AuditLogRepoContract = audit_log_repo

    def run(self, input_data: UpdateBookingCommand) -> BookingView:
        if (
            input_data.contact_name is not None
            and not str(input_data.contact_name).strip()
        ):
            raise ValidationFailedError("The customer's name cannot be empty.")

        inputs: SchedulingInputs = self._transition.scheduling_inputs(
            input_data.business_id
        )
        now: Microseconds = self._transition.now()
        with self._transition.locked_booking(
            input_data.business_id, input_data.booking_id
        ) as booking:
            held_before: FreedPlace | None = held_place_of(booking)
            is_changed: bool = self._apply_placement(booking, input_data, inputs, now)
            is_changed = apply_notes_change(booking, input_data.notes) or is_changed
            is_changed = (
                apply_status_change(
                    booking, input_data.status, input_data.actor_id, now
                )
                or is_changed
            )
            if is_changed:
                self._transition.record(booking, input_data.actor_id, now)

            contact: ContactDocument | None = self._transition.contact_of(booking)
            if contact is not None and input_data.contact_name is not None:
                contact = update_contact_details(
                    self._contact_repo,
                    self._audit_log_repo,
                    contact,
                    ContactDetails(input_data.contact_name, None),
                    input_data.actor_id,
                    now,
                )

        if is_changed:
            self._transition.announce(booking, held_before, now)

        return self._transition.view(booking, inputs, contact)

    def _apply_placement(
        self,
        booking: BookingDocument,
        command: UpdateBookingCommand,
        inputs: SchedulingInputs,
        now: Microseconds,
    ) -> bool:
        """New party size and resource, checked against the booked time."""

        party_size: PartySize = (
            booking.party_size if command.party_size is None else command.party_size
        )
        is_resource_changed: bool = (
            command.resource_id is not None
            and command.resource_id != booking.resource_id
        )
        if party_size == booking.party_size and not is_resource_changed:
            return False

        if booking.status not in BLOCKING_BOOKING_STATUSES:
            raise ConflictError(
                f"A {booking.status} booking can no longer change its place or "
                "party size."
            )

        current: ResourceDocument | None = find_resource(
            inputs.resources, booking.resource_id
        )
        target: ResourceDocument | None = current
        if is_resource_changed:
            target = select_resources(
                inputs.resources, command.resource_id, None, inputs.rules
            )[0]
            if current is not None and target.booking_unit is not current.booking_unit:
                raise ValidationFailedError(
                    f"{target.name} is booked by {booking_unit_label(target)}, "
                    f"unlike {current.name}; make a new booking instead."
                )

        if target is None:
            raise NotFoundError(f"Resource {booking.resource_id} was not found.")

        if int(target.capacity) < int(party_size):
            raise ValidationFailedError(
                f"{target.name} seats at most {int(target.capacity)} guests, "
                f"not {int(party_size)}."
            )

        if is_resource_changed:
            ensure_free_at_booked_time(
                booking,
                target,
                inputs,
                self._transition.bookings_on_booked_date(booking, inputs, now),
            )
            booking.resource_id = target.id

        booking.party_size = party_size
        return True
