from typed_time_provider import Microseconds, WallClock

from app.contracts.operations import (
    BookingCalendarSyncFacilitatorContract,
    BusinessLockRegistryContract,
)
from app.contracts.repositories import (
    AuditLogRepoContract,
    BookingRepoContract,
    BusinessRepoContract,
    ContactRepoContract,
    ResourceRepoContract,
)
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.constants.bookings import BookingStatus
from app.schemas.constants.compliance import AuditAction
from app.schemas.domain.bookings import BookingDocument
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.dto.bookings import BookingView
from app.schemas.dto.operations import UpdateBookingStatusCommand
from app.schemas.exceptions.application_errors import ConflictError, NotFoundError
from app.schemas.typings.compliance.strings import AuditEntityName
from app.use_cases.bookings.operations_support import (
    build_audit_entry,
    require_business,
)
from app.utilities.scheduling.availability import BLOCKING_BOOKING_STATUSES
from app.utilities.scheduling.booking_views import build_booking_view
from app.utilities.scheduling.zoned_time import load_time_zone

BOOKING_ENTITY: AuditEntityName = AuditEntityName("booking")
# Target status -> statuses it may be reached from.
ALLOWED_TRANSITIONS: dict[BookingStatus, frozenset[BookingStatus]] = {
    BookingStatus.COMPLETED: BLOCKING_BOOKING_STATUSES,
    BookingStatus.NO_SHOW: BLOCKING_BOOKING_STATUSES,
    BookingStatus.CANCELLED: BLOCKING_BOOKING_STATUSES,
    BookingStatus.CONFIRMED: frozenset({BookingStatus.PENDING}),
}


class UpdateBookingStatusUseCase(
    UseCaseContract[UpdateBookingStatusCommand, BookingView]
):
    """
    Staff marks a booking COMPLETED, NO_SHOW or CANCELLED (from PENDING or
    CONFIRMED) or confirms a PENDING one. Setting the current status again is
    a no-op; other changes raise ConflictError. The calendar event follows
    (deleted on cancel, created on confirm) and the change is audited.
    """

    def __init__(
        self,
        business_repo: BusinessRepoContract,
        booking_repo: BookingRepoContract,
        resource_repo: ResourceRepoContract,
        contact_repo: ContactRepoContract,
        audit_log_repo: AuditLogRepoContract,
        lock_registry: BusinessLockRegistryContract,
        calendar_sync: BookingCalendarSyncFacilitatorContract,
        wall_clock: WallClock[Microseconds],
    ) -> None:
        self._business_repo: BusinessRepoContract = business_repo
        self._booking_repo: BookingRepoContract = booking_repo
        self._resource_repo: ResourceRepoContract = resource_repo
        self._contact_repo: ContactRepoContract = contact_repo
        self._audit_log_repo: AuditLogRepoContract = audit_log_repo
        self._lock_registry: BusinessLockRegistryContract = lock_registry
        self._calendar_sync: BookingCalendarSyncFacilitatorContract = calendar_sync
        self._wall_clock: WallClock[Microseconds] = wall_clock

    def run(self, input_data: UpdateBookingStatusCommand) -> BookingView:
        business: BusinessDocument = require_business(
            self._business_repo, input_data.business_id
        )
        now: Microseconds = self._wall_clock.now_unix()
        with self._lock_registry.lock_for(business.id):
            booking: BookingDocument | None = self._booking_repo.get(
                business.id, input_data.booking_id
            )
            if booking is None:
                raise NotFoundError(f"Booking {input_data.booking_id} was not found.")

            is_changed: bool = booking.status is not input_data.status
            if is_changed:
                allowed_from: frozenset[BookingStatus] = ALLOWED_TRANSITIONS.get(
                    input_data.status, frozenset()
                )
                if booking.status not in allowed_from:
                    raise ConflictError(
                        f"A {booking.status} booking cannot become {input_data.status}."
                    )

                booking.status = input_data.status
                booking.updated_at = now
                self._booking_repo.save(booking)
                self._audit_log_repo.append(
                    build_audit_entry(
                        business.id,
                        input_data.actor_id,
                        AuditAction.UPDATE,
                        BOOKING_ENTITY,
                        str(booking.id),
                        now,
                    )
                )

        if is_changed and not booking.is_sandbox:
            self._calendar_sync.sync(booking)

        return build_booking_view(
            booking,
            business.timezone,
            load_time_zone(business.timezone),
            self._resource_repo.get(business.id, booking.resource_id),
            self._contact_repo.get(business.id, booking.contact_id),
        )
