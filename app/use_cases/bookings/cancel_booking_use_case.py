from datetime import date

from typed_time_provider import Microseconds, WallClock

from app.contracts.localization_utilities import PhoneNumberParserContract
from app.contracts.operations import (
    BookingCalendarSyncFacilitatorContract,
    BusinessLockRegistryContract,
    ManagerBroadcastFacilitatorContract,
)
from app.contracts.repositories.booking_repositories import BookingRepoContract
from app.contracts.repositories.business_repositories import (
    BusinessProfileRepoContract,
    BusinessRepoContract,
)
from app.contracts.repositories.conversation_repositories import ContactRepoContract
from app.contracts.repositories.knowledge_repositories import (
    ResourceRepoContract,
    ScheduleExceptionRepoContract,
)
from app.contracts.transformer_contract import TransformerContract
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.constants.bookings import BookingStatus
from app.schemas.domain.bookings import BookingDocument
from app.schemas.domain.resources import ResourceDocument
from app.schemas.dto.bookings import BookingResult, BookingView, CancelBookingCommand
from app.schemas.dto.operations.message_texts import (
    BookingMessageInput,
    BookingStaffNotificationInput,
)
from app.schemas.exceptions.application_errors import ConflictError
from app.schemas.typings.conversations.strings import MessageText
from app.use_cases.bookings.booking_support import (
    SchedulingInputs,
    booking_unit_of,
    find_resource,
    find_target_booking,
    load_scheduling_inputs,
    notify_staff_about_booking,
)
from app.utilities.scheduling.availability import BLOCKING_BOOKING_STATUSES
from app.utilities.scheduling.booking_views import build_booking_view
from app.utilities.scheduling.zoned_time import (
    microseconds_to_seconds,
    parse_local_date,
)


class CancelBookingUseCase(UseCaseContract[CancelBookingCommand, BookingResult]):
    """
    Cancel a booking found by id, or by the customer's contact or phone and
    date (model tool cancel_booking and the cabinet).

    A command that carries the customer's contact or phone is a customer
    request: the booking must be theirs and staff are notified. A command
    with only a booking id comes from the cabinet. Cancelling twice is
    harmless; completed and no-show bookings cannot be cancelled. The
    confirmation quotes the profile's cancellation policy.
    """

    def __init__(
        self,
        business_repo: BusinessRepoContract,
        business_profile_repo: BusinessProfileRepoContract,
        resource_repo: ResourceRepoContract,
        schedule_exception_repo: ScheduleExceptionRepoContract,
        booking_repo: BookingRepoContract,
        contact_repo: ContactRepoContract,
        lock_registry: BusinessLockRegistryContract,
        phone_number_parser: PhoneNumberParserContract,
        confirmation_transformer: TransformerContract[BookingMessageInput, MessageText],
        staff_notification_transformer: TransformerContract[
            BookingStaffNotificationInput, MessageText
        ],
        manager_broadcaster: ManagerBroadcastFacilitatorContract,
        calendar_sync: BookingCalendarSyncFacilitatorContract,
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
        self._lock_registry: BusinessLockRegistryContract = lock_registry
        self._phone_number_parser: PhoneNumberParserContract = phone_number_parser
        self._confirmation_transformer: TransformerContract[
            BookingMessageInput, MessageText
        ] = confirmation_transformer
        self._staff_notification_transformer: TransformerContract[
            BookingStaffNotificationInput, MessageText
        ] = staff_notification_transformer
        self._manager_broadcaster: ManagerBroadcastFacilitatorContract = (
            manager_broadcaster
        )
        self._calendar_sync: BookingCalendarSyncFacilitatorContract = calendar_sync
        self._wall_clock: WallClock[Microseconds] = wall_clock

    def run(self, input_data: CancelBookingCommand) -> BookingResult:
        inputs: SchedulingInputs = load_scheduling_inputs(
            self._business_repo,
            self._business_profile_repo,
            self._resource_repo,
            self._schedule_exception_repo,
            input_data.business_id,
        )
        local_date: date | None = (
            None if input_data.date is None else parse_local_date(input_data.date)
        )
        now: Microseconds = self._wall_clock.now_unix()
        with self._lock_registry.lock_for(input_data.business_id):
            booking: BookingDocument = find_target_booking(
                self._booking_repo,
                self._contact_repo,
                input_data.business_id,
                inputs.zone,
                input_data.booking_id,
                input_data.contact_id,
                input_data.contact_phone_number,
                local_date,
                microseconds_to_seconds(int(now)),
                is_sandbox=input_data.is_sandbox,
            )
            is_newly_cancelled: bool = booking.status is not BookingStatus.CANCELLED
            if is_newly_cancelled:
                if booking.status not in BLOCKING_BOOKING_STATUSES:
                    raise ConflictError(
                        f"The booking is {booking.status} and can no longer be "
                        "cancelled."
                    )

                booking.status = BookingStatus.CANCELLED
                booking.updated_at = now
                self._booking_repo.save(booking)

        resource: ResourceDocument | None = find_resource(
            inputs.resources, booking.resource_id
        )
        view: BookingView = build_booking_view(
            booking,
            inputs.business.timezone,
            inputs.zone,
            resource,
            self._contact_repo.get(input_data.business_id, booking.contact_id),
        )
        if is_newly_cancelled and not booking.is_sandbox:
            is_customer_request: bool = (
                input_data.contact_id is not None
                or input_data.contact_phone_number is not None
            )
            if is_customer_request:
                notify_staff_about_booking(
                    self._manager_broadcaster,
                    self._staff_notification_transformer,
                    self._phone_number_parser,
                    inputs.business,
                    view,
                )

            self._calendar_sync.sync(booking)

        return BookingResult(
            booking=view,
            confirmation_text=self._confirmation_transformer.transform(
                BookingMessageInput(
                    business_name=inputs.business.name,
                    booking=view,
                    booking_unit=booking_unit_of(resource),
                    language=input_data.language,
                    cancellation_policy=(
                        None
                        if inputs.rules is None
                        else inputs.rules.cancellation_policy
                    ),
                )
            ),
        )
