"""Booking use cases built over the operations world's store."""

from app.contracts.operations import BookingCalendarSyncFacilitatorContract
from app.transformers.notifications.booking_cancelled_notification_transformer import (
    BookingCancelledNotificationTransformer,
)
from app.transformers.notifications.booking_confirmation_transformer import (
    BookingConfirmationTransformer,
)
from app.transformers.notifications.booking_moved_notification_transformer import (
    BookingMovedNotificationTransformer,
)
from app.transformers.notifications.cancellation_confirmation_transformer import (
    CancellationConfirmationTransformer,
)
from app.transformers.notifications.new_booking_notification_transformer import (
    NewBookingNotificationTransformer,
)
from app.transformers.notifications.reschedule_confirmation_transformer import (
    RescheduleConfirmationTransformer,
)
from app.transformers.notifications.staff_alert_brief_transformer import (
    StaffAlertBriefTransformer,
)
from app.use_cases.bookings.cancel_booking_use_case import CancelBookingUseCase
from app.use_cases.bookings.check_availability_use_case import CheckAvailabilityUseCase
from app.use_cases.bookings.create_booking_use_case import CreateBookingUseCase
from app.use_cases.bookings.list_bookings_use_case import ListBookingsUseCase
from app.use_cases.bookings.manual_booking.create_manual_booking_use_case import (
    CreateManualBookingUseCase,
)
from app.use_cases.bookings.reschedule_booking_use_case import RescheduleBookingUseCase
from app.use_cases.bookings.update_booking_use_case import UpdateBookingUseCase
from tests.operations.operations_seeding import OperationsSeeding


class OperationsBookingFactories(OperationsSeeding):
    """The seeded store with factories for every booking use case."""

    def check_availability(self) -> CheckAvailabilityUseCase:
        return CheckAvailabilityUseCase(
            business_repo=self.business_repo,
            business_profile_repo=self.profile_repo,
            resource_repo=self.resource_repo,
            schedule_exception_repo=self.exception_repo,
            booking_repo=self.booking_repo,
            wall_clock=self.clock.wall_clock,
        )

    def create_booking(
        self,
        calendar_sync: BookingCalendarSyncFacilitatorContract | None = None,
    ) -> CreateBookingUseCase:
        return CreateBookingUseCase(
            business_repo=self.business_repo,
            business_profile_repo=self.profile_repo,
            resource_repo=self.resource_repo,
            schedule_exception_repo=self.exception_repo,
            booking_repo=self.booking_repo,
            contact_repo=self.contact_repo,
            audit_log_repo=self.audit_repo,
            lock_registry=self.lock_registry,
            phone_number_parser=self.phone_parser,
            confirmation_transformer=BookingConfirmationTransformer(self.resolver),
            staff_notification_transformer=NewBookingNotificationTransformer(
                self.resolver
            ),
            staff_brief_transformer=StaffAlertBriefTransformer(self.resolver),
            staff_alerts=self.staff_alerts,
            calendar_sync=calendar_sync or self.calendar_sync,
            live_events=self.live_events,
            wall_clock=self.clock.wall_clock,
        )

    def cancel_booking(self) -> CancelBookingUseCase:
        return CancelBookingUseCase(
            business_repo=self.business_repo,
            business_profile_repo=self.profile_repo,
            resource_repo=self.resource_repo,
            schedule_exception_repo=self.exception_repo,
            booking_repo=self.booking_repo,
            contact_repo=self.contact_repo,
            lock_registry=self.lock_registry,
            phone_number_parser=self.phone_parser,
            confirmation_transformer=CancellationConfirmationTransformer(self.resolver),
            staff_notification_transformer=BookingCancelledNotificationTransformer(
                self.resolver
            ),
            staff_brief_transformer=StaffAlertBriefTransformer(self.resolver),
            staff_alerts=self.staff_alerts,
            calendar_sync=self.calendar_sync,
            live_events=self.live_events,
            wall_clock=self.clock.wall_clock,
        )

    def reschedule_booking(self) -> RescheduleBookingUseCase:
        return RescheduleBookingUseCase(
            business_repo=self.business_repo,
            business_profile_repo=self.profile_repo,
            resource_repo=self.resource_repo,
            schedule_exception_repo=self.exception_repo,
            booking_repo=self.booking_repo,
            contact_repo=self.contact_repo,
            lock_registry=self.lock_registry,
            phone_number_parser=self.phone_parser,
            confirmation_transformer=RescheduleConfirmationTransformer(self.resolver),
            staff_notification_transformer=BookingMovedNotificationTransformer(
                self.resolver
            ),
            staff_brief_transformer=StaffAlertBriefTransformer(self.resolver),
            staff_alerts=self.staff_alerts,
            calendar_sync=self.calendar_sync,
            live_events=self.live_events,
            wall_clock=self.clock.wall_clock,
        )

    def list_bookings(self) -> ListBookingsUseCase:
        return ListBookingsUseCase(
            business_repo=self.business_repo,
            booking_repo=self.booking_repo,
            resource_repo=self.resource_repo,
            contact_repo=self.contact_repo,
            audit_log_repo=self.audit_repo,
            wall_clock=self.clock.wall_clock,
        )

    def create_manual_booking(self) -> CreateManualBookingUseCase:
        return CreateManualBookingUseCase(
            business_repo=self.business_repo,
            business_profile_repo=self.profile_repo,
            resource_repo=self.resource_repo,
            schedule_exception_repo=self.exception_repo,
            booking_repo=self.booking_repo,
            contact_repo=self.contact_repo,
            conversation_repo=self.conversation_repo,
            audit_log_repo=self.audit_repo,
            lock_registry=self.lock_registry,
            phone_number_parser=self.phone_parser,
            confirmation_transformer=BookingConfirmationTransformer(self.resolver),
            calendar_sync=self.calendar_sync,
            live_events=self.live_events,
            wall_clock=self.clock.wall_clock,
        )

    def update_booking(self) -> UpdateBookingUseCase:
        return UpdateBookingUseCase(
            business_repo=self.business_repo,
            business_profile_repo=self.profile_repo,
            schedule_exception_repo=self.exception_repo,
            booking_repo=self.booking_repo,
            resource_repo=self.resource_repo,
            contact_repo=self.contact_repo,
            audit_log_repo=self.audit_repo,
            lock_registry=self.lock_registry,
            calendar_sync=self.calendar_sync,
            live_events=self.live_events,
            wall_clock=self.clock.wall_clock,
        )
