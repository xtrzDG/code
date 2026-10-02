from datetime import date

from typed_time_provider import Microseconds, WallClock

from app.contracts.localization_utilities import PhoneNumberParserContract
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
from app.contracts.repositories.conversation_repositories import (
    ContactRepoContract,
    ConversationRepoContract,
)
from app.contracts.repositories.knowledge_repositories import (
    ResourceRepoContract,
    ScheduleExceptionRepoContract,
)
from app.contracts.transformer_contract import TransformerContract
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.constants.bookings import BookingRefusalCode, BookingStatus
from app.schemas.constants.compliance import AuditAction
from app.schemas.domain.bookings import BookingDocument
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.domain.contacts import ContactDocument
from app.schemas.domain.conversations import ConversationDocument
from app.schemas.domain.resources import ResourceDocument
from app.schemas.dto.bookings import BookingResult, BookingView
from app.schemas.dto.operations.bookings import ManualBookingCommand
from app.schemas.dto.operations.message_texts import BookingMessageInput
from app.schemas.exceptions.application_errors import (
    NotFoundError,
    ValidationFailedError,
)
from app.schemas.typings.bookings.constrained_integers import (
    BookingEndsAtUnixSeconds,
    BookingStartsAtUnixSeconds,
)
from app.schemas.typings.compliance.strings import AuditEntityName
from app.schemas.typings.conversations.booleans import IsSandboxConversation
from app.schemas.typings.conversations.strings import MessageText
from app.schemas.typings.localization.constrained_strings import (
    E164PhoneNumber,
    LanguageTag,
)
from app.use_cases.bookings.booking_support import (
    SchedulingInputs,
    load_scheduling_inputs,
)
from app.use_cases.bookings.operations_support import (
    CONTACT_ENTITY,
    ContactDetails,
    build_audit_entry,
    require_contact,
    update_contact_details,
)
from app.utilities.scheduling.booking_placement import place_booking
from app.utilities.scheduling.booking_views import build_booking_view
from app.utilities.scheduling.placement import Placement
from app.utilities.scheduling.placement_errors import booking_refusal_reason
from app.utilities.scheduling.placement_request import PlacementRequest
from app.utilities.scheduling.resource_selection import (
    seating_resources,
    select_resources,
)
from app.utilities.scheduling.zoned_time import (
    microseconds_to_seconds,
    parse_local_date,
    parse_time_of_day,
)

BOOKING_ENTITY: AuditEntityName = AuditEntityName("booking")


class CreateManualBookingUseCase(UseCaseContract[ManualBookingCommand, BookingResult]):
    """
    Booking added by staff in the cabinet (concept: manual adding).

    The phone may be typed in any format and is parsed with the given
    country hint (the business country when omitted). Booked from a
    conversation card (`conversation_id`), the booking is linked to that
    conversation, made for its customer (name and phone updated) and comes
    from its channel; otherwise a contact with the phone is reused, else a
    new one is created. Opening hours and capacity are enforced under the
    business lock; the online-booking limits (minimum notice, maximum party)
    are not. The customer's language (given, else the contact's, else the
    business default) is stored for later texts and used for the
    confirmation. The booking and the contact change are audited with the
    staff member.
    """

    def __init__(
        self,
        business_repo: BusinessRepoContract,
        business_profile_repo: BusinessProfileRepoContract,
        resource_repo: ResourceRepoContract,
        schedule_exception_repo: ScheduleExceptionRepoContract,
        booking_repo: BookingRepoContract,
        contact_repo: ContactRepoContract,
        conversation_repo: ConversationRepoContract,
        audit_log_repo: AuditLogRepoContract,
        lock_registry: BusinessLockRegistryContract,
        phone_number_parser: PhoneNumberParserContract,
        confirmation_transformer: TransformerContract[BookingMessageInput, MessageText],
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
        self._conversation_repo: ConversationRepoContract = conversation_repo
        self._audit_log_repo: AuditLogRepoContract = audit_log_repo
        self._lock_registry: BusinessLockRegistryContract = lock_registry
        self._phone_number_parser: PhoneNumberParserContract = phone_number_parser
        self._confirmation_transformer: TransformerContract[
            BookingMessageInput, MessageText
        ] = confirmation_transformer
        self._calendar_sync: BookingCalendarSyncFacilitatorContract = calendar_sync
        self._wall_clock: WallClock[Microseconds] = wall_clock

    def run(self, input_data: ManualBookingCommand) -> BookingResult:
        inputs: SchedulingInputs = load_scheduling_inputs(
            self._business_repo,
            self._business_profile_repo,
            self._resource_repo,
            self._schedule_exception_repo,
            input_data.business_id,
        )
        phone_number: E164PhoneNumber | None = None
        if input_data.contact_phone_number is not None:
            phone_number = self._phone_number_parser.parse(
                input_data.contact_phone_number,
                input_data.country_hint or inputs.business.country_code,
            ).e164

        conversation: ConversationDocument | None = self._find_conversation(input_data)
        existing_contact: ContactDocument | None
        if conversation is not None:
            existing_contact = require_contact(
                self._contact_repo, input_data.business_id, conversation.contact_id
            )
        elif phone_number is not None:
            existing_contact = self._contact_repo.find_by_phone_number(
                input_data.business_id, phone_number
            )
        else:
            existing_contact = None

        is_sandbox: IsSandboxConversation = (
            conversation is not None and conversation.is_sandbox
        )
        local_date: date = parse_local_date(input_data.date)
        candidates: list[ResourceDocument] = seating_resources(
            select_resources(
                inputs.resources,
                input_data.resource_id,
                input_data.resource_kind,
                inputs.rules,
            ),
            input_data.party_size,
        )
        if not candidates:
            message: str = (
                f"No bookable resource seats {int(input_data.party_size)} guests."
            )
            raise ValidationFailedError(
                message,
                reasons=[
                    booking_refusal_reason(
                        BookingRefusalCode.NO_SEATING_RESOURCE,
                        message,
                        [str(int(input_data.party_size))],
                    )
                ],
            )

        now: Microseconds = self._wall_clock.now_unix()
        contact: ContactDocument = existing_contact or ContactDocument(
            business_id=input_data.business_id,
            name=input_data.contact_name,
            phone_number=phone_number,
            language=input_data.language,
            created_at=now,
            updated_at=now,
        )
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
                    duration_minutes=input_data.duration_minutes,
                    nights=(
                        None if input_data.nights is None else int(input_data.nights)
                    ),
                    zone=inputs.zone,
                    business_hours=inputs.business_hours,
                    exceptions=inputs.exceptions,
                    bookings=self._booking_repo.list_by_business(
                        input_data.business_id
                    ),
                    rules=inputs.rules,
                    stay_times=inputs.stay_times,
                    earliest_start=microseconds_to_seconds(int(now)),
                    include_sandbox=is_sandbox,
                ),
            )
            contact = self._store_contact(
                contact, existing_contact, input_data, phone_number, now
            )
            language: LanguageTag = customer_language(
                input_data, contact, conversation, inputs.business
            )
            booking = BookingDocument(
                business_id=input_data.business_id,
                resource_id=placement.resource.id,
                contact_id=contact.id,
                conversation_id=None if conversation is None else conversation.id,
                starts_at=BookingStartsAtUnixSeconds(placement.starts_at),
                ends_at=BookingEndsAtUnixSeconds(placement.ends_at),
                party_size=input_data.party_size,
                status=BookingStatus.CONFIRMED,
                source_channel=(
                    input_data.source_channel
                    if conversation is None
                    else conversation.channel
                ),
                notes=input_data.notes,
                is_sandbox=is_sandbox,
                language=language,
                created_at=now,
                updated_at=now,
            )
            self._booking_repo.save(booking)

        self._audit_log_repo.append(
            build_audit_entry(
                booking.business_id,
                input_data.actor_id,
                AuditAction.CREATE,
                BOOKING_ENTITY,
                str(booking.id),
                now,
            )
        )
        view: BookingView = build_booking_view(
            booking,
            inputs.business.timezone,
            inputs.zone,
            placement.resource,
            contact,
        )
        if not booking.is_sandbox:
            self._calendar_sync.sync(booking)

        return BookingResult(
            booking=view,
            confirmation_text=self._confirmation_transformer.transform(
                BookingMessageInput(
                    business_name=inputs.business.name,
                    booking=view,
                    booking_unit=placement.resource.booking_unit,
                    language=language,
                )
            ),
        )

    def _find_conversation(
        self,
        command: ManualBookingCommand,
    ) -> ConversationDocument | None:
        if command.conversation_id is None:
            return None

        conversation: ConversationDocument | None = self._conversation_repo.get(
            command.business_id, command.conversation_id
        )
        if conversation is None:
            raise NotFoundError(
                f"Conversation {command.conversation_id} was not found."
            )

        return conversation

    def _store_contact(
        self,
        contact: ContactDocument,
        existing_contact: ContactDocument | None,
        command: ManualBookingCommand,
        phone_number: E164PhoneNumber | None,
        now: Microseconds,
    ) -> ContactDocument:
        """
        Save a new contact, or update the name of a reused one (and its phone
        when booking for a conversation's customer).
        """

        if existing_contact is not None:
            return update_contact_details(
                self._contact_repo,
                self._audit_log_repo,
                existing_contact,
                ContactDetails(
                    command.contact_name,
                    None if command.conversation_id is None else phone_number,
                ),
                command.actor_id,
                now,
            )

        self._contact_repo.save(contact)
        self._audit_log_repo.append(
            build_audit_entry(
                contact.business_id,
                command.actor_id,
                AuditAction.CREATE,
                CONTACT_ENTITY,
                str(contact.id),
                now,
            )
        )
        return contact


def customer_language(
    command: ManualBookingCommand,
    contact: ContactDocument,
    conversation: ConversationDocument | None,
    business: BusinessDocument,
) -> LanguageTag:
    """Given, else the contact's, else the conversation's, else the default."""

    if command.language is not None:
        return command.language

    if contact.language is not None:
        return contact.language

    if conversation is not None and conversation.language is not None:
        return conversation.language

    return business.default_language
