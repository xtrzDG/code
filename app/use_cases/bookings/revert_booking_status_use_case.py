"""Staff undo the last status change they made to a booking."""

from datetime import date

from typed_time_provider import Microseconds, WallClock

from app.contracts.growth import GrowthBookingsFacilitatorContract
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
from app.schemas.constants.compliance import AuditAction
from app.schemas.constants.live_events import LiveEventKind
from app.schemas.domain.bookings import BookingDocument, BookingStatusChange
from app.schemas.domain.resources import ResourceDocument
from app.schemas.dto.bookings import BookingView
from app.schemas.dto.operations.bookings import RevertBookingStatusCommand
from app.schemas.exceptions.application_errors import NotFoundError
from app.schemas.typings.compliance.strings import AuditEntityName
from app.use_cases.bookings.booking_support import (
    SchedulingInputs,
    find_resource,
    load_scheduling_inputs,
)
from app.use_cases.bookings.bookings_in_play import HeldPlaces, bookings_not_over_on
from app.use_cases.bookings.freed_places import held_place_of, notice_if_freed
from app.use_cases.bookings.status_undo import (
    ensure_time_still_free,
    require_undoable,
    takes_time_again,
)
from app.use_cases.shared.operations_support import build_audit_entry
from app.utilities.scheduling.booking_views import build_booking_view
from app.utilities.scheduling.zoned_time import to_local_moment

BOOKING_ENTITY: AuditEntityName = AuditEntityName("booking")


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
    business hear of it, and the calendar event follows.
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
        growth: GrowthBookingsFacilitatorContract,
        wall_clock: WallClock[Microseconds],
    ) -> None:
        self._growth: GrowthBookingsFacilitatorContract = growth
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
        self._live_events: EventPublisherFacilitatorContract = live_events
        self._wall_clock: WallClock[Microseconds] = wall_clock

    def run(self, input_data: RevertBookingStatusCommand) -> BookingView:
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

            change: BookingStatusChange = require_undoable(
                booking, input_data.status, now
            )
            resource: ResourceDocument | None = find_resource(
                inputs.resources, booking.resource_id
            )
            if takes_time_again(booking, change):
                starts_on: date = to_local_moment(
                    int(booking.starts_at), inputs.zone
                ).date()
                ensure_time_still_free(
                    booking,
                    resource,
                    bookings_not_over_on(
                        self._booking_repo,
                        booking.business_id,
                        starts_on,
                        inputs.zone,
                        HeldPlaces(self._growth, now, booking.contact_id),
                    ),
                )

            before = held_place_of(booking)
            booking.status = change.previous_status
            booking.last_status_change = None
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

        self._live_events.publish(
            booking.business_id,
            LiveEventKind.BOOKING_CHANGED,
            (booking.id,),
            is_sandbox=booking.is_sandbox,
        )
        if not booking.is_sandbox:
            self._calendar_sync.sync(booking)
            notice_if_freed(self._growth, before, booking, now, True)

        return build_booking_view(
            booking,
            inputs.business.timezone,
            inputs.zone,
            resource,
            self._contact_repo.get(booking.business_id, booking.contact_id),
        )
