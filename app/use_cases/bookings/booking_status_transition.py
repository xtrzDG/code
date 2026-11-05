from collections.abc import Generator
from contextlib import contextmanager
from datetime import date

from typed_time_provider import Microseconds, WallClock

from app.contracts.calendar_sync import CalendarBusyTimesRepoContract
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
from app.schemas.constants.compliance import AuditAction
from app.schemas.constants.live_events import LiveEventKind
from app.schemas.domain.bookings import BookingDocument
from app.schemas.domain.contacts import ContactDocument
from app.schemas.dto.bookings import BookingView
from app.schemas.dto.growth.freed_places import FreedPlace
from app.schemas.exceptions.application_errors import NotFoundError
from app.schemas.typings.bookings.prefixed_id import BookingId
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.compliance.strings import AuditEntityName
from app.schemas.typings.users.prefixed_id import UserId
from app.use_cases.bookings.booking_support import (
    SchedulingInputs,
    find_resource,
    load_scheduling_inputs,
)
from app.use_cases.bookings.bookings_in_play import HeldPlaces, bookings_not_over_on
from app.use_cases.bookings.freed_places import notice_if_freed
from app.use_cases.shared.operations_support import build_audit_entry
from app.utilities.scheduling.booking_views import build_booking_view
from app.utilities.scheduling.zoned_time import to_local_moment

BOOKING_ENTITY: AuditEntityName = AuditEntityName("booking")


class BookingStatusTransition:
    """
    The steps every staff change of a booking goes through, in order, for
    a change from the cabinet and for its Undo: the business's scheduling
    inputs; the booking read under the business's booking lock; the
    bookings its booked date competes with; the change saved with one
    audit entry naming the staff member; then, outside the lock, the
    cabinets told, the calendar event synced and a place the change freed
    offered to the waitlist.
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
        busy_times_repo: CalendarBusyTimesRepoContract,
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
        self._live_events: EventPublisherFacilitatorContract = live_events
        self._growth: GrowthBookingsFacilitatorContract = growth
        self._busy_times_repo: CalendarBusyTimesRepoContract = busy_times_repo
        self._wall_clock: WallClock[Microseconds] = wall_clock

    def now(self) -> Microseconds:
        return self._wall_clock.now_unix()

    def scheduling_inputs(self, business_id: BusinessId) -> SchedulingInputs:
        return load_scheduling_inputs(
            self._business_repo,
            self._business_profile_repo,
            self._resource_repo,
            self._schedule_exception_repo,
            business_id,
            self._busy_times_repo,
        )

    @contextmanager
    def locked_booking(
        self,
        business_id: BusinessId,
        booking_id: BookingId,
    ) -> Generator[BookingDocument]:
        """The booking as stored, read and changed under the booking lock."""

        with self._lock_registry.lock_for(business_id):
            booking: BookingDocument | None = self._booking_repo.get(
                business_id, booking_id
            )
            if booking is None:
                raise NotFoundError(f"Booking {booking_id} was not found.")

            yield booking

    def bookings_on_booked_date(
        self,
        booking: BookingDocument,
        inputs: SchedulingInputs,
        now: Microseconds,
    ) -> list[BookingDocument]:
        """What the booking's time competes with (live waitlist holds too)."""

        starts_on: date = to_local_moment(int(booking.starts_at), inputs.zone).date()
        return bookings_not_over_on(
            self._booking_repo,
            booking.business_id,
            starts_on,
            inputs.zone,
            HeldPlaces(self._growth, now, booking.contact_id),
        )

    def record(
        self,
        booking: BookingDocument,
        actor_id: UserId,
        now: Microseconds,
    ) -> None:
        """Save the changed booking with one audit entry (under the lock)."""

        booking.updated_at = now
        self._booking_repo.save(booking)
        self._audit_log_repo.append(
            build_audit_entry(
                booking.business_id,
                actor_id,
                AuditAction.UPDATE,
                BOOKING_ENTITY,
                str(booking.id),
                now,
            )
        )

    def announce(
        self,
        booking: BookingDocument,
        held_before: FreedPlace | None,
        now: Microseconds,
    ) -> None:
        """After the lock: cabinets, the calendar event, a freed place."""

        self._live_events.publish(
            booking.business_id,
            LiveEventKind.BOOKING_CHANGED,
            (booking.id,),
            is_sandbox=booking.is_sandbox,
        )
        if not booking.is_sandbox:
            self._calendar_sync.sync(booking)
            notice_if_freed(self._growth, held_before, booking, now, True)

    def contact_of(self, booking: BookingDocument) -> ContactDocument | None:
        return self._contact_repo.get(booking.business_id, booking.contact_id)

    def view(
        self,
        booking: BookingDocument,
        inputs: SchedulingInputs,
        contact: ContactDocument | None,
    ) -> BookingView:
        return build_booking_view(
            booking,
            inputs.business.timezone,
            inputs.zone,
            find_resource(inputs.resources, booking.resource_id),
            contact,
        )
