from typed_time_provider import Microseconds, WallClock

from app.contracts.localization_utilities import PhoneNumberParserContract
from app.contracts.repositories.business_repositories import BusinessRepoContract
from app.contracts.repositories.compliance_repositories import AuditLogRepoContract
from app.contracts.repositories.conversation_repositories import ContactRepoContract
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.constants.channels import ChannelKind
from app.schemas.constants.compliance import AuditAction
from app.schemas.constants.integrations import ApiKeyScope
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.domain.contacts import ContactDocument
from app.schemas.dto.bookings import CreateLeadCommand
from app.schemas.dto.public_api.commands import PublicLeadCommand
from app.schemas.exceptions.application_errors import InvalidPhoneNumberError
from app.schemas.typings.compliance.strings import AuditEntityName
from app.schemas.typings.localization.constrained_strings import E164PhoneNumber
from app.use_cases.integrations.api_key_records import require_scope
from app.use_cases.integrations.public_api.public_access import key_business
from app.use_cases.shared.operations_support import build_audit_entry
from app.utilities.channels.channel_phone_numbers import parse_messaging_phone_number

CONTACT_ENTITY: AuditEntityName = AuditEntityName("contact")
INVALID_PHONE_MESSAGE: str = "contact_phone_number is not a phone number."


class StartPublicLeadUseCase(UseCaseContract[PublicLeadCommand, CreateLeadCommand]):
    """
    A lead the API sends (a website form, a CRM): its customer is the
    contact with the phone (in the business's country unless it has a
    country code), else a new contact (audited); the lead use case then
    stores it and tells the staff. Needs `leads:write`.
    """

    def __init__(
        self,
        business_repo: BusinessRepoContract,
        contact_repo: ContactRepoContract,
        audit_log_repo: AuditLogRepoContract,
        phone_number_parser: PhoneNumberParserContract,
        wall_clock: WallClock[Microseconds],
    ) -> None:
        self._business_repo: BusinessRepoContract = business_repo
        self._contact_repo: ContactRepoContract = contact_repo
        self._audit_log_repo: AuditLogRepoContract = audit_log_repo
        self._phone_number_parser: PhoneNumberParserContract = phone_number_parser
        self._wall_clock: WallClock[Microseconds] = wall_clock

    def run(self, input_data: PublicLeadCommand) -> CreateLeadCommand:
        require_scope(input_data.principal, ApiKeyScope.LEADS_WRITE)
        business = key_business(self._business_repo, input_data.principal)
        request = input_data.request
        phone_number = self._phone_number(business, input_data)
        contact = self._contact(business, input_data, phone_number)
        return CreateLeadCommand(
            business_id=business.id,
            contact_id=contact.id,
            contact_name=request.contact_name,
            contact_phone_number=phone_number,
            lead_type=request.type,
            details=request.details,
            requested_date=request.requested_date,
            party_size=request.party_size,
            budget=request.budget,
            source_channel=ChannelKind.PHONE,
            language=request.language or contact.language or business.default_language,
        )

    def _phone_number(
        self, business: BusinessDocument, input_data: PublicLeadCommand
    ) -> E164PhoneNumber | None:
        raw = input_data.request.contact_phone_number
        if raw is None:
            return None

        parsed = parse_messaging_phone_number(
            self._phone_number_parser, str(raw), business.country_code
        )
        if parsed is None:
            raise InvalidPhoneNumberError(INVALID_PHONE_MESSAGE)

        return parsed

    def _contact(
        self,
        business: BusinessDocument,
        input_data: PublicLeadCommand,
        phone_number: E164PhoneNumber | None,
    ) -> ContactDocument:
        if phone_number is not None:
            found = self._contact_repo.find_by_phone_number(business.id, phone_number)
            if found is not None and found.erased_at is None:
                return found

        now: Microseconds = self._wall_clock.now_unix()
        contact = ContactDocument(
            business_id=business.id,
            name=input_data.request.contact_name,
            phone_number=phone_number,
            language=input_data.request.language,
            created_at=now,
            updated_at=now,
        )
        self._contact_repo.save(contact)
        self._audit_log_repo.append(
            build_audit_entry(
                business.id,
                input_data.principal.created_by,
                AuditAction.CREATE,
                CONTACT_ENTITY,
                str(contact.id),
                now,
                input_data.principal.client_ip_address,
            )
        )
        return contact
