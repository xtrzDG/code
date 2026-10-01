from datetime import date

from typed_time_provider import Microseconds, WallClock

from app.contracts.localization_utilities import PhoneNumberParserContract
from app.contracts.operations import (
    BookingCalendarSyncFacilitatorContract,
    BusinessLockRegistryContract,
)
from app.contracts.repositories import (
    AuditLogRepoContract,
    BookingRepoContract,
    BusinessProfileRepoContract,
    BusinessRepoContract,
    ContactRepoContract,
    ResourceRepoContract,
    ScheduleExceptionRepoContract,
)
from app.contracts.transformer_contract import TransformerContract
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.constants.bookings import BookingStatus
from app.schemas.constants.compliance import AuditAction
from app.schemas.domain.bookings import BookingDocument
from app.schemas.domain.contacts import ContactDocument
from app.schemas.domain.resources import ResourceDocument
from app.schemas.dto.bookings import BookingResult, BookingView
from app.schemas.dto.operations import BookingMessageInput, ManualBookingCommand
from app.schemas.exceptions.application_errors import ValidationFailedError
from app.schemas.typings.bookings.constrained_integers import (
    BookingEndsAtUnixSeconds,
    BookingStartsAtUnixSeconds,
)
from app.schemas.typings.compliance.strings import AuditEntityName
from app.schemas.typings.conversations.strings import MessageText
from app.schemas.typings.localization.constrained_strings import E164PhoneNumber
from app.use_cases.bookings.booking_support import (
    SchedulingInputs,
    load_scheduling_inputs,
)
from app.use_cases.bookings.operations_support import (
    CONTACT_ENTITY,
    ContactDetails,
    build_audit_entry,
    update_contact_details,
)
from app.utilities.scheduling.booking_placement import (
    Placement,
    PlacementRequest,
    place_booking,
    seating_resources,
    select_resources,
)
from app.utilities.scheduling.booking_views import build_booking_view
from app.utilities.scheduling.zoned_time import (
    microseconds_to_seconds,
    parse_local_date,
    parse_time_of_day,
)

BOOKING_ENTITY: AuditEntityName = AuditEntityName("booking")


class CreateManualBookingUseCase(UseCaseContract[ManualBookingCommand, BookingResult]):
    """
    Booking added by staff in the cabinet (concept: manual adding).

    The phone may be typed in any format and is parsed with the business
    country as a hint; a contact with that phone is reused, else a new one is
    created. Opening hours and capacity are enforced under the business lock;
    the online-booking limits (minimum notice, maximum party) are not. The
    booking and the contact change are audited with the staff member.
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
                input_data.contact_phone_number, inputs.business.country_code
            ).e164

        existing_contact: ContactDocument | None = (
            None
            if phone_number is None
            else self._contact_repo.find_by_phone_number(
                input_data.business_id, phone_number
            )
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
            raise ValidationFailedError(
                f"No bookable resource seats {int(input_data.party_size)} guests."
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
                    include_sandbox=False,
                ),
            )
            self._store_contact(contact, existing_contact, input_data, now)
            booking = BookingDocument(
                business_id=input_data.business_id,
                resource_id=placement.resource.id,
                contact_id=contact.id,
                starts_at=BookingStartsAtUnixSeconds(placement.starts_at),
                ends_at=BookingEndsAtUnixSeconds(placement.ends_at),
                party_size=input_data.party_size,
                status=BookingStatus.CONFIRMED,
                source_channel=input_data.source_channel,
                notes=input_data.notes,
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
        self._calendar_sync.sync(booking)
        return BookingResult(
            booking=view,
            confirmation_text=self._confirmation_transformer.transform(
                BookingMessageInput(
                    business_name=inputs.business.name,
                    booking=view,
                    booking_unit=placement.resource.booking_unit,
                    language=input_data.language or inputs.business.default_language,
                )
            ),
        )

    def _store_contact(
        self,
        contact: ContactDocument,
        existing_contact: ContactDocument | None,
        command: ManualBookingCommand,
        now: Microseconds,
    ) -> None:
        if existing_contact is not None:
            update_contact_details(
                self._contact_repo,
                self._audit_log_repo,
                existing_contact,
                ContactDetails(command.contact_name, None),
                command.actor_id,
                now,
            )
            return

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
