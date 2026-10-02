"""Staff change a booking in the cabinet."""

from datetime import datetime

from typed_time_provider import Microseconds, WallClock

from app.contracts.live_events import EventPublisherFacilitatorContract
from app.contracts.operations import (
    BookingCalendarSyncFacilitatorContract,
    BusinessLockRegistryContract,
)
from app.contracts.repositories.booking_repositories import BookingRepoContract
from app.contracts.repositories.business_repositories import (
    BusinessProfileRepoContract,
    BusinessRepoContract,
)
from app.contracts.repositories.compliance_repositories import AuditLogRepoContract
from app.contracts.repositories.conversation_repositories import ContactRepoContract
from app.contracts.repositories.knowledge_repositories import (
    ResourceRepoContract,
    ScheduleExceptionRepoContract,
)
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.constants.bookings import BookingUnit
from app.schemas.constants.compliance import AuditAction
from app.schemas.constants.live_events import LiveEventKind
from app.schemas.domain.bookings import BookingDocument
from app.schemas.domain.contacts import ContactDocument
from app.schemas.domain.resources import ResourceDocument
from app.schemas.dto.bookings import BookingView
from app.schemas.dto.operations.bookings import UpdateBookingCommand
from app.schemas.exceptions.application_errors import (
    ConflictError,
    NotFoundError,
    ValidationFailedError,
)
from app.schemas.typings.bookings.constrained_integers import (
    BookingDurationMinutes,
    PartySize,
)
from app.schemas.typings.compliance.strings import AuditEntityName
from app.use_cases.bookings.booking_edits import (
    apply_notes_change,
    apply_status_change,
    booking_unit_label,
)
from app.use_cases.bookings.booking_support import (
    SchedulingInputs,
    find_resource,
    load_scheduling_inputs,
    stay_night_count,
)
from app.use_cases.bookings.operations_support import (
    ContactDetails,
    build_audit_entry,
    update_contact_details,
)
from app.utilities.scheduling.availability import BLOCKING_BOOKING_STATUSES
from app.utilities.scheduling.booking_placement import place_booking
from app.utilities.scheduling.booking_views import build_booking_view
from app.utilities.scheduling.placement_request import PlacementRequest
from app.utilities.scheduling.resource_selection import select_resources
from app.utilities.scheduling.zoned_time import (
    SECONDS_PER_MINUTE,
    minute_of_day,
    to_local_moment,
)

BOOKING_ENTITY: AuditEntityName = AuditEntityName("booking")


class UpdateBookingUseCase(UseCaseContract[UpdateBookingCommand, BookingView]):
    """
    Staff change a booking in the cabinet; omitted fields stay as they are.

    - Status: COMPLETED, NO_SHOW or CANCELLED (from PENDING or CONFIRMED),
      or CONFIRMED for a PENDING booking. Setting the current status again
      is a no-op; other changes raise ConflictError.
    - Party size and resource, only while the booking is PENDING or
      CONFIRMED: the resource must be active, booked the same way (time
      slots or nights), seat the party, be open at the booked time and have
      a free unit then (the booking itself not counted). The online-booking
      limits (notice, maximum party) do not apply to staff, as for manual
      bookings. The time is changed by rescheduling.
    - Notes: an empty text removes them.
    - Contact name: renames the customer (audited as a contact change).

    Checks and writes run under the business lock. The booking change is
    audited once with the staff member, and the calendar event follows.
    """

    def __init__(
        self,
        business_repo: BusinessRepoContract,
        business_profile_repo: BusinessProfileRepoContract,
        resource_repo: ResourceRepoContract,
        schedule_exception_repo: ScheduleExceptionRepoContract,
        booking_repo: BookingRepoContract,
        contact_repo: ContactRepoContract,
        audit_log_repo: AuditLogRepoContract,
        lock_registry: BusinessLockRegistryContract,
        calendar_sync: BookingCalendarSyncFacilitatorContract,
        live_events: EventPublisherFacilitatorContract,
        wall_clock: WallClock[Microseconds],
    ) -> None:
        self._business_repo: BusinessRepoContract = business_repo
        self._business_profile_repo: BusinessProfileRepoContract = business_profile_repo
        self._resource_repo: ResourceRepoContract = resource_repo
        self._schedule_exception_repo: ScheduleExceptionRepoContract = (
            schedule_exception_repo
        )
        self._booking_repo: BookingRepoContract = booking_repo
        self._contact_repo: ContactRepoContract = contact_repo
        self._audit_log_repo: AuditLogRepoContract = audit_log_repo
        self._lock_registry: BusinessLockRegistryContract = lock_registry
        self._calendar_sync: BookingCalendarSyncFacilitatorContract = calendar_sync
        self._wall_clock: WallClock[Microseconds] = wall_clock
        self._live_events: EventPublisherFacilitatorContract = live_events

    def run(self, input_data: UpdateBookingCommand) -> BookingView:
        if (
            input_data.contact_name is not None
            and not str(input_data.contact_name).strip()
        ):
            raise ValidationFailedError("The customer's name cannot be empty.")

        inputs: SchedulingInputs = load_scheduling_inputs(
            self._business_repo,
            self._business_profile_repo,
            self._resource_repo,
            self._schedule_exception_repo,
            input_data.business_id,
        )
        now: Microseconds = self._wall_clock.now_unix()
        with self._lock_registry.lock_for(input_data.business_id):
            booking: BookingDocument | None = self._booking_repo.get(
                input_data.business_id, input_data.booking_id
            )
            if booking is None:
                raise NotFoundError(f"Booking {input_data.booking_id} was not found.")

            is_changed: bool = self._apply_placement(booking, input_data, inputs)
            is_changed = apply_notes_change(booking, input_data.notes) or is_changed
            is_changed = apply_status_change(booking, input_data.status) or is_changed
            if is_changed:
                booking.updated_at = now
                self._booking_repo.save(booking)
                self._audit_log_repo.append(
                    build_audit_entry(
                        booking.business_id,
                        input_data.actor_id,
                        AuditAction.UPDATE,
                        BOOKING_ENTITY,
                        str(booking.id),
                        now,
                    )
                )

            contact: ContactDocument | None = self._contact_repo.get(
                booking.business_id, booking.contact_id
            )
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
            self._live_events.publish(
                booking.business_id,
                LiveEventKind.BOOKING_CHANGED,
                (booking.id,),
                is_sandbox=booking.is_sandbox,
            )

        if is_changed and not booking.is_sandbox:
            self._calendar_sync.sync(booking)

        return build_booking_view(
            booking,
            inputs.business.timezone,
            inputs.zone,
            find_resource(inputs.resources, booking.resource_id),
            contact,
        )

    def _apply_placement(
        self,
        booking: BookingDocument,
        command: UpdateBookingCommand,
        inputs: SchedulingInputs,
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
            self._ensure_free(booking, target, inputs)
            booking.resource_id = target.id

        booking.party_size = party_size
        return True

    def _ensure_free(
        self,
        booking: BookingDocument,
        target: ResourceDocument,
        inputs: SchedulingInputs,
    ) -> None:
        """The target is open and has a free unit for the booked time."""

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
                bookings=self._booking_repo.list_by_business(booking.business_id),
                rules=inputs.rules,
                stay_times=inputs.stay_times,
                earliest_start=0,
                include_sandbox=booking.is_sandbox,
                excluded_booking_id=booking.id,
            ),
        )
