from typed_time_provider import Microseconds, WallClock

from app.contracts.localization_utilities import PhoneNumberParserContract
from app.contracts.operations import ManagerBroadcastFacilitatorContract
from app.contracts.repositories import (
    AuditLogRepoContract,
    BusinessRepoContract,
    ContactRepoContract,
    LeadRepoContract,
)
from app.contracts.transformer_contract import TransformerContract
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.constants.bookings import LeadStatus
from app.schemas.domain.bookings import LeadDocument
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.domain.contacts import ContactDocument
from app.schemas.dto.bookings import CreateLeadCommand, LeadView
from app.schemas.dto.operations import LeadStaffNotificationInput
from app.schemas.typings.conversations.strings import MessageText
from app.schemas.typings.localization.constrained_strings import LanguageTag
from app.schemas.typings.localization.strings import FormattedPhoneNumber
from app.use_cases.bookings.operations_support import (
    ContactDetails,
    build_staff_messages,
    display_phone,
    require_business,
    require_contact,
    update_contact_details,
)
from app.use_cases.leads.lead_views import build_lead_view


class CreateLeadUseCase(UseCaseContract[CreateLeadCommand, LeadView]):
    """
    Request for a manager (model tool create_lead): banquets, groups,
    corporate events and anything non-standard. The contact's name and phone
    are updated; real (non-sandbox) leads notify every staff contact in their
    language. Notification failures never lose the lead.
    """

    def __init__(
        self,
        business_repo: BusinessRepoContract,
        lead_repo: LeadRepoContract,
        contact_repo: ContactRepoContract,
        audit_log_repo: AuditLogRepoContract,
        phone_number_parser: PhoneNumberParserContract,
        staff_notification_transformer: TransformerContract[
            LeadStaffNotificationInput, MessageText
        ],
        manager_broadcaster: ManagerBroadcastFacilitatorContract,
        wall_clock: WallClock[Microseconds],
    ) -> None:
        self._business_repo: BusinessRepoContract = business_repo
        self._lead_repo: LeadRepoContract = lead_repo
        self._contact_repo: ContactRepoContract = contact_repo
        self._audit_log_repo: AuditLogRepoContract = audit_log_repo
        self._phone_number_parser: PhoneNumberParserContract = phone_number_parser
        self._staff_notification_transformer: TransformerContract[
            LeadStaffNotificationInput, MessageText
        ] = staff_notification_transformer
        self._manager_broadcaster: ManagerBroadcastFacilitatorContract = (
            manager_broadcaster
        )
        self._wall_clock: WallClock[Microseconds] = wall_clock

    def run(self, input_data: CreateLeadCommand) -> LeadView:
        business: BusinessDocument = require_business(
            self._business_repo, input_data.business_id
        )
        contact: ContactDocument = require_contact(
            self._contact_repo, business.id, input_data.contact_id
        )
        now: Microseconds = self._wall_clock.now_unix()
        lead = LeadDocument(
            business_id=business.id,
            contact_id=contact.id,
            conversation_id=input_data.conversation_id,
            lead_type=input_data.lead_type,
            details=input_data.details,
            requested_date=input_data.requested_date,
            party_size=input_data.party_size,
            budget=input_data.budget,
            source_channel=input_data.source_channel,
            status=LeadStatus.NEW,
            is_sandbox=input_data.is_sandbox,
            created_at=now,
            updated_at=now,
        )
        self._lead_repo.save(lead)
        contact = update_contact_details(
            self._contact_repo,
            self._audit_log_repo,
            contact,
            ContactDetails(input_data.contact_name, input_data.contact_phone_number),
            None,
            now,
        )
        view: LeadView = build_lead_view(lead)
        if not lead.is_sandbox:
            self._notify_staff(business, view, contact)

        return view

    def _notify_staff(
        self,
        business: BusinessDocument,
        view: LeadView,
        contact: ContactDocument,
    ) -> None:
        phone: FormattedPhoneNumber | None = display_phone(
            self._phone_number_parser, contact.phone_number
        )

        def render(language: LanguageTag) -> MessageText:
            return self._staff_notification_transformer.transform(
                LeadStaffNotificationInput(
                    business_name=business.name,
                    lead=view,
                    contact_name=contact.name,
                    contact_phone_display=phone,
                    language=language,
                )
            )

        self._manager_broadcaster.broadcast(build_staff_messages(business, render))
