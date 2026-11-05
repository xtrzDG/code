from datetime import date

from typed_time_provider import Microseconds, WallClock

from app.contracts.growth import GrowthBookingsFacilitatorContract
from app.contracts.live_events import EventPublisherFacilitatorContract
from app.contracts.localization_utilities import PhoneNumberParserContract
from app.contracts.notifications import StaffAlertFacilitatorContract
from app.contracts.operations import (
    BookingCalendarSyncFacilitatorContract,
    BusinessLockRegistryContract,
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
from app.schemas.constants.live_events import LiveEventKind
from app.schemas.constants.notifications import StaffBookingChange
from app.schemas.domain.bookings import BookingDocument
from app.schemas.domain.resources import ResourceDocument
from app.schemas.dto.bookings import BookingResult, BookingView, CancelBookingCommand
from app.schemas.dto.growth.freed_places import FreedPlace
from app.schemas.dto.notifications.staff_alerts import (
    StaffAlertBrief,
    StaffAlertBriefInput,
)
from app.schemas.dto.operations.message_texts import (
    BookingMessageInput,
    BookingStaffNotificationInput,
)
from app.schemas.exceptions.application_errors import ConflictError
from app.schemas.typings.conversations.strings import MessageText
from app.use_cases.bookings.booking_requesters import (
    BookingRequester,
    CustomerRequester,
    StaffRequester,
    customer_contact_of,
    customer_phone_of,
    requester_of,
    staff_actor_of,
)
from app.use_cases.bookings.booking_results import confirmed_change
from app.use_cases.bookings.booking_support import (
    SchedulingInputs,
    booking_unit_of,
    find_resource,
    find_target_booking,
    load_scheduling_inputs,
    notify_staff_about_booking,
)
from app.use_cases.bookings.booking_versions import refuse_changed_booking
from app.use_cases.bookings.freed_places import held_place_of, notice_if_freed
from app.use_cases.bookings.status_undo import note_status_change
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

    Who asks decides the authority (`requester_of`): a customer (the
    command's contact or phone) cancels only their own booking, never from
    a phone call, and staff are notified; a staff member (`actor_id`, from
    the cabinet) cancels any booking by its id and may undo it for a short
    while (RevertBookingStatusUseCase); a command naming neither is refused
    (AccessDeniedError). Cancelling twice is
    harmless; completed and no-show bookings cannot be cancelled. The
    confirmation quotes the profile's cancellation policy. The freed place
    goes to the waitlist (a staff cancellation a little later, for Undo).
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
        staff_brief_transformer: TransformerContract[
            StaffAlertBriefInput, StaffAlertBrief
        ],
        staff_alerts: StaffAlertFacilitatorContract,
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
        self._lock_registry: BusinessLockRegistryContract = lock_registry
        self._phone_number_parser: PhoneNumberParserContract = phone_number_parser
        self._confirmation_transformer: TransformerContract[
            BookingMessageInput, MessageText
        ] = confirmation_transformer
        self._staff_notification_transformer: TransformerContract[
            BookingStaffNotificationInput, MessageText
        ] = staff_notification_transformer
        self._staff_brief_transformer: TransformerContract[
            StaffAlertBriefInput, StaffAlertBrief
        ] = staff_brief_transformer
        self._staff_alerts: StaffAlertFacilitatorContract = staff_alerts
        self._calendar_sync: BookingCalendarSyncFacilitatorContract = calendar_sync
        self._wall_clock: WallClock[Microseconds] = wall_clock
        self._live_events: EventPublisherFacilitatorContract = live_events

    def run(self, input_data: CancelBookingCommand) -> BookingResult:
        requester: BookingRequester = requester_of(input_data)
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
                customer_contact_of(requester),
                customer_phone_of(requester),
                local_date,
                microseconds_to_seconds(int(now)),
                is_sandbox=input_data.is_sandbox,
            )
            refuse_changed_booking(booking, input_data.expected_starts_at)
            before: FreedPlace | None = held_place_of(booking)
            is_newly_cancelled: bool = booking.status is not BookingStatus.CANCELLED
            if is_newly_cancelled:
                if booking.status not in BLOCKING_BOOKING_STATUSES:
                    raise ConflictError(
                        f"The booking is {booking.status} and can no longer be "
                        "cancelled."
                    )

                note_status_change(
                    booking, booking.status, staff_actor_of(requester), now
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
        if is_newly_cancelled:
            self._live_events.publish(
                booking.business_id,
                LiveEventKind.BOOKING_CHANGED,
                (booking.id,),
                is_sandbox=booking.is_sandbox,
            )

        if is_newly_cancelled and not booking.is_sandbox:
            if isinstance(requester, CustomerRequester):
                notify_staff_about_booking(
                    self._staff_alerts,
                    self._staff_notification_transformer,
                    self._staff_brief_transformer,
                    self._phone_number_parser,
                    inputs.business,
                    view,
                    StaffBookingChange.CANCELLED,
                )

            self._calendar_sync.sync(booking)
            notice_if_freed(
                self._growth,
                before,
                booking,
                now,
                isinstance(requester, StaffRequester),
            )

        return confirmed_change(
            self._confirmation_transformer,
            inputs,
            view,
            booking_unit_of(resource),
            input_data.language,
        )
