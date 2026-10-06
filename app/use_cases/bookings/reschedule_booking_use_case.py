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
    KnowledgeItemRepoContract,
    ResourceRepoContract,
    ScheduleExceptionRepoContract,
)
from app.contracts.transformer_contract import TransformerContract
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.constants.bookings import BookingUnit
from app.schemas.constants.live_events import LiveEventKind
from app.schemas.constants.notifications import StaffBookingChange
from app.schemas.domain.bookings import BookingDocument
from app.schemas.domain.knowledge import KnowledgeItemDocument
from app.schemas.domain.resources import ResourceDocument
from app.schemas.dto.bookings import (
    BookingResult,
    BookingView,
    RescheduleBookingCommand,
)
from app.schemas.dto.notifications.staff_alerts import (
    StaffAlertBrief,
    StaffAlertBriefInput,
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
    BookingEndsAtUnixSeconds,
    BookingStartsAtUnixSeconds,
    NightCount,
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
from app.use_cases.bookings.booking_versions import refuse_changed_booking
from app.use_cases.bookings.bookings_in_play import HeldPlaces, bookings_not_over_on
from app.use_cases.bookings.freed_places import held_place_of, notice_if_freed
from app.use_cases.bookings.moved_placements import place_moved_booking
from app.use_cases.bookings.reschedule_candidates import (
    booked_offer,
    reprice_stay,
)
from app.utilities.scheduling.availability import BLOCKING_BOOKING_STATUSES
from app.utilities.scheduling.booking_views import build_booking_view
from app.utilities.scheduling.placement import Placement
from app.utilities.scheduling.resource_selection import min_notice_seconds
from app.utilities.scheduling.zoned_time import (
    microseconds_to_seconds,
    parse_local_date,
)


class RescheduleBookingUseCase(
    UseCaseContract[RescheduleBookingCommand, BookingResult]
):
    """
    Move a booking found by id, or by the customer's contact or phone and old
    date, to a new local date (and time for slots), keeping its length or
    number of nights (model tool reschedule_booking and the cabinet).

    The same resource is preferred; another free performer of the booked
    service (or resource of the same kind) that seats the party is used
    when it is taken, and the service's buffer still applies. A moved stay
    is priced again for its new nights. Availability is checked
    under the business lock without counting the booking itself. Customer
    requests follow the online-booking notice and notify staff; cabinet
    moves (booking id only) do not. The confirmation quotes the profile's
    cancellation policy. Places held for other waiting customers count as
    taken, and the place the booking leaves goes to the waitlist.
    """

    def __init__(
        self,
        business_repo: BusinessRepoContract,
        business_profile_repo: BusinessProfileRepoContract,
        resource_repo: ResourceRepoContract,
        schedule_exception_repo: ScheduleExceptionRepoContract,
        booking_repo: BookingRepoContract,
        knowledge_item_repo: KnowledgeItemRepoContract,
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
        self._knowledge_item_repo: KnowledgeItemRepoContract = knowledge_item_repo
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
        items: list[KnowledgeItemDocument] = self._knowledge_item_repo.list_by_business(
            input_data.business_id
        )
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
            refuse_changed_booking(booking, input_data.expected_starts_at)
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

            before = held_place_of(booking)
            offer: KnowledgeItemDocument | None = booked_offer(booking, items)
            nights: int = stay_night_count(booking, inputs.zone)
            placement: Placement = place_moved_booking(
                inputs,
                booking,
                current,
                offer,
                items,
                new_date,
                input_data.new_time,
                bookings_not_over_on(
                    self._booking_repo,
                    input_data.business_id,
                    new_date,
                    inputs.zone,
                    HeldPlaces(self._growth, now, booking.contact_id),
                ),
                (
                    now_seconds + min_notice_seconds(inputs.rules)
                    if is_customer_request
                    else now_seconds
                ),
            )
            reprice_stay(
                booking,
                offer,
                placement.resource.booking_unit,
                new_date,
                NightCount(nights),
                inputs.business.currency_code,
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
            offer,
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
                    self._staff_alerts,
                    self._staff_notification_transformer,
                    self._staff_brief_transformer,
                    self._phone_number_parser,
                    inputs.business,
                    view,
                    StaffBookingChange.MOVED,
                )

            self._calendar_sync.sync(booking)
            notice_if_freed(self._growth, before, booking, now, not is_customer_request)

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
