from datetime import date

from typed_time_provider import Microseconds, WallClock

from app.contracts.calendar_sync import CalendarBusyTimesRepoContract
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
from app.contracts.repositories.compliance_repositories import AuditLogRepoContract
from app.contracts.repositories.conversation_repositories import ContactRepoContract
from app.contracts.repositories.knowledge_repositories import (
    KnowledgeItemRepoContract,
    ResourceRepoContract,
    ScheduleExceptionRepoContract,
)
from app.contracts.transformer_contract import TransformerContract
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.constants.bookings import BookingStatus
from app.schemas.constants.live_events import LiveEventKind
from app.schemas.constants.notifications import StaffBookingChange
from app.schemas.domain.bookings import BookingDocument
from app.schemas.domain.contacts import ContactDocument
from app.schemas.domain.knowledge import KnowledgeItemDocument
from app.schemas.domain.resources import ResourceDocument
from app.schemas.dto.bookings import BookingResult, BookingView, CreateBookingCommand
from app.schemas.dto.notifications.staff_alerts import (
    StaffAlertBrief,
    StaffAlertBriefInput,
)
from app.schemas.dto.operations.message_texts import (
    BookingMessageInput,
    BookingStaffNotificationInput,
)
from app.schemas.typings.bookings.constrained_integers import (
    BookingEndsAtUnixSeconds,
    BookingStartsAtUnixSeconds,
)
from app.schemas.typings.conversations.strings import MessageText
from app.use_cases.bookings.booking_support import (
    SchedulingInputs,
    load_scheduling_inputs,
    notify_staff_about_booking,
)
from app.use_cases.bookings.bookings_in_play import HeldPlaces, bookings_not_over_on
from app.use_cases.bookings.offer_selection import (
    BookedOffer,
    OfferChoice,
    OfferRequest,
    choose_offer,
    price_placement,
    require_seating,
)
from app.use_cases.shared.operations_support import (
    ContactDetails,
    require_contact,
    update_contact_details,
)
from app.utilities.scheduling.booking_placement import place_booking
from app.utilities.scheduling.booking_views import build_booking_view
from app.utilities.scheduling.placement import Placement
from app.utilities.scheduling.placement_request import PlacementRequest
from app.utilities.scheduling.resource_selection import (
    ensure_party_size_allowed,
    min_notice_seconds,
)
from app.utilities.scheduling.zoned_time import (
    microseconds_to_seconds,
    parse_local_date,
    parse_time_of_day,
)


class CreateBookingUseCase(UseCaseContract[CreateBookingCommand, BookingResult]):
    """
    Book a resource for a customer (model tool create_booking).

    The availability check is repeated under the business lock, so two
    customers cannot take the last unit; a taken time raises ConflictError.
    A named service (id or name in any script) books its full length with
    one of its performers (a named one, "Nino" or "ნინო", must perform it)
    and keeps the performer blocked for its buffer afterwards; the booking
    stores the service and its value (the price, or a stay's nights at
    their seasonal rates). The contact's name and phone are updated, the
    booking is CONFIRMED, and the result carries a confirmation in the
    customer's language repeating the date, time, name and party size in
    the business time zone. Real (non-sandbox) bookings notify every staff
    contact and are pushed to the connected calendar; neither can break the
    booking. Places held for other waiting customers count as taken; a
    booking of the customer's own held place, or one after a rebooking
    invitation, is marked as the waitlist's or the campaign's (`origin`).
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
        audit_log_repo: AuditLogRepoContract,
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
        busy_times_repo: CalendarBusyTimesRepoContract,
        wall_clock: WallClock[Microseconds],
    ) -> None:
        self._growth: GrowthBookingsFacilitatorContract = growth
        self._busy_times_repo: CalendarBusyTimesRepoContract = busy_times_repo
        self._business_repo: BusinessRepoContract = business_repo
        self._business_profile_repo: BusinessProfileRepoContract = business_profile_repo
        self._resource_repo: ResourceRepoContract = resource_repo
        self._schedule_exception_repo: ScheduleExceptionRepoContract = (
            schedule_exception_repo
        )
        self._booking_repo: BookingRepoContract = booking_repo
        self._knowledge_item_repo: KnowledgeItemRepoContract = knowledge_item_repo
        self._contact_repo: ContactRepoContract = contact_repo
        self._audit_log_repo: AuditLogRepoContract = audit_log_repo
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

    def run(self, input_data: CreateBookingCommand) -> BookingResult:
        inputs: SchedulingInputs = load_scheduling_inputs(
            self._business_repo,
            self._business_profile_repo,
            self._resource_repo,
            self._schedule_exception_repo,
            input_data.business_id,
            self._busy_times_repo,
        )
        ensure_party_size_allowed(input_data.party_size, inputs.rules)
        contact: ContactDocument = require_contact(
            self._contact_repo, input_data.business_id, input_data.contact_id
        )
        local_date: date = parse_local_date(input_data.date)
        items: list[KnowledgeItemDocument] = self._knowledge_item_repo.list_by_business(
            input_data.business_id
        )
        choice: OfferChoice = choose_offer(
            inputs,
            items,
            OfferRequest(
                service_reference=input_data.service_reference,
                resource_reference=input_data.resource_reference,
                resource_id=input_data.resource_id,
                resource_kind=input_data.resource_kind,
                duration_minutes=input_data.duration_minutes,
            ),
        )
        candidates: list[ResourceDocument] = require_seating(
            choice.candidates,
            input_data.party_size,
            "; pass the request to a manager",
        )
        now: Microseconds = self._wall_clock.now_unix()
        with self._lock_registry.lock_for(input_data.business_id):
            placement: Placement = place_booking(
                candidates,
                PlacementRequest(
                    local_date=local_date,
                    minute_of_day=(
                        None
                        if input_data.time is None
                        else parse_time_of_day(input_data.time)
                    ),
                    duration_minutes=choice.duration_minutes,
                    nights=None
                    if input_data.nights is None
                    else int(input_data.nights),
                    zone=inputs.zone,
                    business_hours=inputs.business_hours,
                    exceptions=inputs.exceptions,
                    bookings=bookings_not_over_on(
                        self._booking_repo,
                        input_data.business_id,
                        local_date,
                        inputs.zone,
                        HeldPlaces(self._growth, now, contact.id),
                    ),
                    rules=inputs.rules,
                    stay_times=inputs.stay_times,
                    earliest_start=microseconds_to_seconds(int(now))
                    + min_notice_seconds(inputs.rules),
                    include_sandbox=input_data.is_sandbox,
                    sandbox_conversation_id=input_data.conversation_id,
                    buffer_minutes=choice.buffer_minutes,
                    blocked_times=inputs.blocked_times,
                ),
            )
            booked: BookedOffer = price_placement(
                choice,
                placement,
                items,
                local_date,
                input_data.nights,
                inputs,
            )
            booking = BookingDocument(
                business_id=input_data.business_id,
                resource_id=placement.resource.id,
                contact_id=contact.id,
                conversation_id=input_data.conversation_id,
                starts_at=BookingStartsAtUnixSeconds(placement.starts_at),
                ends_at=BookingEndsAtUnixSeconds(placement.ends_at),
                party_size=input_data.party_size,
                status=BookingStatus.CONFIRMED,
                source_channel=input_data.source_channel,
                notes=input_data.notes,
                is_sandbox=input_data.is_sandbox,
                language=input_data.language,
                service_item_id=booked.service_item_id,
                buffer_minutes=choice.buffer_minutes,
                value_minor=booked.value_minor,
                currency_code=booked.currency_code,
                created_at=now,
                updated_at=now,
            )
            booking.origin = self._growth.attribute(booking, now)
            self._booking_repo.save(booking)

        contact = update_contact_details(
            self._contact_repo,
            self._audit_log_repo,
            contact,
            ContactDetails(input_data.contact_name, input_data.contact_phone_number),
            None,
            now,
        )
        view: BookingView = build_booking_view(
            booking,
            inputs.business.timezone,
            inputs.zone,
            placement.resource,
            contact,
            booked.offer,
        )
        self._live_events.publish(
            booking.business_id,
            LiveEventKind.BOOKING_CREATED,
            (booking.id,),
            is_sandbox=booking.is_sandbox,
        )
        if not input_data.is_sandbox:
            notify_staff_about_booking(
                self._staff_alerts,
                self._staff_notification_transformer,
                self._staff_brief_transformer,
                self._phone_number_parser,
                inputs.business,
                view,
                StaffBookingChange.CREATED,
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
                )
            ),
        )
