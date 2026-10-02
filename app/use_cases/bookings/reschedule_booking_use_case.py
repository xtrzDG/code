from datetime import date

from typed_time_provider import Microseconds, WallClock

from app.contracts.live_events import EventPublisherFacilitatorContract
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
from app.schemas.constants.bookings import BookingUnit
from app.schemas.constants.live_events import LiveEventKind
from app.schemas.domain.bookings import BookingDocument
from app.schemas.domain.resources import ResourceDocument
from app.schemas.dto.bookings import (
    BookingResult,
    BookingView,
    RescheduleBookingCommand,
)
from app.schemas.dto.operations.message_texts import (
    BookingMessageInput,
    BookingStaffNotificationInput,
)
from app.schemas.exceptions.application_errors import (
    ConflictError,
    NotFoundError,
    ValidationFailedError,
)
from app.schemas.typings.bookings.constrained_integers import (
    BookingDurationMinutes,
    BookingEndsAtUnixSeconds,
    BookingStartsAtUnixSeconds,
)
from app.schemas.typings.conversations.strings import MessageText
from app.use_cases.bookings.booking_support import (
    SchedulingInputs,
    find_resource,
    find_target_booking,
    load_scheduling_inputs,
    notify_staff_about_booking,
    stay_night_count,
)
from app.utilities.scheduling.availability import BLOCKING_BOOKING_STATUSES
from app.utilities.scheduling.booking_placement import place_booking
from app.utilities.scheduling.booking_views import build_booking_view
from app.utilities.scheduling.placement import Placement
from app.utilities.scheduling.placement_request import PlacementRequest
from app.utilities.scheduling.resource_selection import (
    min_notice_seconds,
    seating_resources,
)
from app.utilities.scheduling.zoned_time import (
    SECONDS_PER_MINUTE,
    microseconds_to_seconds,
    parse_local_date,
    parse_time_of_day,
)


class RescheduleBookingUseCase(
    UseCaseContract[RescheduleBookingCommand, BookingResult]
):
    """
    Move a booking found by id, or by the customer's contact or phone and old
    date, to a new local date (and time for slots), keeping its length or
    number of nights (model tool reschedule_booking and the cabinet).

    The same resource is preferred; another free resource of the same kind
    that seats the party is used when it is taken. Availability is checked
    under the business lock without counting the booking itself. Customer
    requests follow the online-booking notice and notify staff; cabinet
    moves (booking id only) do not. The confirmation quotes the profile's
    cancellation policy.
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
        self._live_events: EventPublisherFacilitatorContract = live_events

    def run(self, input_data: RescheduleBookingCommand) -> BookingResult:
        inputs: SchedulingInputs = load_scheduling_inputs(
            self._business_repo,
            self._business_profile_repo,
            self._resource_repo,
            self._schedule_exception_repo,
            input_data.business_id,
        )
        is_customer_request: bool = (
            input_data.contact_id is not None
            or input_data.contact_phone_number is not None
        )
        old_date: date | None = (
            None
            if input_data.old_date is None
            else parse_local_date(input_data.old_date)
        )
        new_date: date = parse_local_date(input_data.new_date)
        now: Microseconds = self._wall_clock.now_unix()
        now_seconds: int = microseconds_to_seconds(int(now))
        with self._lock_registry.lock_for(input_data.business_id):
            booking: BookingDocument = find_target_booking(
                self._booking_repo,
                self._contact_repo,
                input_data.business_id,
                inputs.zone,
                input_data.booking_id,
                input_data.contact_id,
                input_data.contact_phone_number,
                old_date,
                now_seconds,
                is_sandbox=input_data.is_sandbox,
            )
            if booking.status not in BLOCKING_BOOKING_STATUSES:
                raise ConflictError(
                    f"The booking is {booking.status} and can no longer be moved."
                )

            current: ResourceDocument | None = find_resource(
                inputs.resources, booking.resource_id
            )
            if current is None:
                raise NotFoundError(f"Resource {booking.resource_id} was not found.")

            if current.booking_unit is BookingUnit.TIME_SLOT and (
                input_data.new_time is None
            ):
                raise ValidationFailedError("A new time is required to move a booking.")

            placement: Placement = place_booking(
                self._candidates(inputs, booking, current),
                PlacementRequest(
                    local_date=new_date,
                    minute_of_day=(
                        None
                        if input_data.new_time is None
                        else parse_time_of_day(input_data.new_time)
                    ),
                    duration_minutes=(
                        BookingDurationMinutes(
                            (int(booking.ends_at) - int(booking.starts_at))
                            // SECONDS_PER_MINUTE
                        )
                        if current.booking_unit is BookingUnit.TIME_SLOT
                        else None
                    ),
                    nights=stay_night_count(booking, inputs.zone),
                    zone=inputs.zone,
                    business_hours=inputs.business_hours,
                    exceptions=inputs.exceptions,
                    bookings=self._booking_repo.list_by_business(
                        input_data.business_id
                    ),
                    rules=inputs.rules,
                    stay_times=inputs.stay_times,
                    earliest_start=(
                        now_seconds + min_notice_seconds(inputs.rules)
                        if is_customer_request
                        else now_seconds
                    ),
                    include_sandbox=booking.is_sandbox,
                    excluded_booking_id=booking.id,
                ),
            )
            booking.resource_id = placement.resource.id
            booking.starts_at = BookingStartsAtUnixSeconds(placement.starts_at)
            booking.ends_at = BookingEndsAtUnixSeconds(placement.ends_at)
            # The new time gets its own reminder.
            booking.reminder_sent_at = None
            booking.updated_at = now
            self._booking_repo.save(booking)

        view: BookingView = build_booking_view(
            booking,
            inputs.business.timezone,
            inputs.zone,
            placement.resource,
            self._contact_repo.get(input_data.business_id, booking.contact_id),
        )
        self._live_events.publish(
            booking.business_id,
            LiveEventKind.BOOKING_CHANGED,
            (booking.id,),
            is_sandbox=booking.is_sandbox,
        )
        if not booking.is_sandbox:
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
                    booking_unit=placement.resource.booking_unit,
                    language=input_data.language,
                    cancellation_policy=(
                        None
                        if inputs.rules is None
                        else inputs.rules.cancellation_policy
                    ),
                )
            ),
        )

    def _candidates(
        self,
        inputs: SchedulingInputs,
        booking: BookingDocument,
        current: ResourceDocument,
    ) -> list[ResourceDocument]:
        """The booked resource first (if active), then same-kind alternatives."""

        alternatives: list[ResourceDocument] = seating_resources(
            [
                resource
                for resource in inputs.resources
                if resource.is_active
                and resource.id != current.id
                and resource.kind is current.kind
                and resource.booking_unit is current.booking_unit
            ],
            booking.party_size,
        )
        if not current.is_active:
            return alternatives

        return [current, *alternatives]
