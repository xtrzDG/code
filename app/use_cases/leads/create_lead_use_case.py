from typed_time_provider import Microseconds, WallClock

from app.contracts.live_events import EventPublisherFacilitatorContract
from app.contracts.localization_utilities import PhoneNumberParserContract
from app.contracts.notifications import StaffAlertFacilitatorContract
from app.contracts.repositories.booking_repositories import LeadRepoContract
from app.contracts.repositories.business_repositories import BusinessRepoContract
from app.contracts.repositories.compliance_repositories import AuditLogRepoContract
from app.contracts.repositories.conversation_repositories import ContactRepoContract
from app.contracts.transformer_contract import TransformerContract
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.constants.bookings import LeadStatus
from app.schemas.constants.live_events import LiveEventKind
from app.schemas.domain.bookings import LeadDocument
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.domain.contacts import ContactDocument
from app.schemas.dto.bookings import CreateLeadCommand, LeadView
from app.schemas.dto.inbox.assignment import (
    AutoAssignCommand,
    AutoAssignResult,
    OpenRequestRefresh,
    OpenRequestState,
)
from app.schemas.dto.notifications.staff_alerts import (
    LeadBrief,
    StaffAlertBrief,
    StaffAlertBriefInput,
)
from app.schemas.dto.operations.message_texts import LeadStaffNotificationInput
from app.schemas.typings.conversations.strings import MessageText
from app.schemas.typings.localization.constrained_strings import LanguageTag
from app.schemas.typings.localization.strings import FormattedPhoneNumber
from app.use_cases.bookings.operations_support import (
    ContactDetails,
    display_phone,
    require_business,
    require_contact,
    update_contact_details,
)
from app.use_cases.inbox.assignment.request_tracking import track_request
from app.use_cases.leads.lead_views import build_lead_view
from app.use_cases.notifications.staff_alerts import StaffAlertTexts, lead_alert


class CreateLeadUseCase(UseCaseContract[CreateLeadCommand, LeadView]):
    """
    Request for a manager (model tool create_lead): banquets, groups,
    corporate events and anything non-standard. The contact's name and phone
    are updated; real (non-sandbox) leads notify every staff contact and
    subscribed device in their language, with a link to the conversation.
    Notification failures never lose the lead. The lead's conversation
    joins the team inbox's "Requests" view and, when the business asked for
    it, is assigned automatically.
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
        live_events: EventPublisherFacilitatorContract,
        staff_brief_transformer: TransformerContract[
            StaffAlertBriefInput, StaffAlertBrief
        ],
        staff_alerts: StaffAlertFacilitatorContract,
        wall_clock: WallClock[Microseconds],
        refresh_open_request: UseCaseContract[OpenRequestRefresh, OpenRequestState],
        auto_assign: UseCaseContract[AutoAssignCommand, AutoAssignResult],
    ) -> None:
        self._business_repo: BusinessRepoContract = business_repo
        self._lead_repo: LeadRepoContract = lead_repo
        self._contact_repo: ContactRepoContract = contact_repo
        self._audit_log_repo: AuditLogRepoContract = audit_log_repo
        self._phone_number_parser: PhoneNumberParserContract = phone_number_parser
        self._staff_notification_transformer: TransformerContract[
            LeadStaffNotificationInput, MessageText
        ] = staff_notification_transformer
        self._staff_brief_transformer: TransformerContract[
            StaffAlertBriefInput, StaffAlertBrief
        ] = staff_brief_transformer
        self._staff_alerts: StaffAlertFacilitatorContract = staff_alerts
        self._wall_clock: WallClock[Microseconds] = wall_clock
        self._live_events: EventPublisherFacilitatorContract = live_events
        self._refresh_open_request: UseCaseContract[
            OpenRequestRefresh, OpenRequestState
        ] = refresh_open_request
        self._auto_assign: UseCaseContract[AutoAssignCommand, AutoAssignResult] = (
            auto_assign
        )

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
        self._live_events.publish(
            lead.business_id,
            LiveEventKind.LEAD_CREATED,
            (lead.id,),
            is_sandbox=lead.is_sandbox,
        )
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
            self._notify_staff(business, lead, view, contact)

        track_request(lead, self._refresh_open_request, self._auto_assign)
        return view

    def _notify_staff(
        self,
        business: BusinessDocument,
        lead: LeadDocument,
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

        def render_brief(language: LanguageTag) -> StaffAlertBrief:
            return self._staff_brief_transformer.transform(
                StaffAlertBriefInput(
                    business_name=business.name,
                    language=language,
                    lead=LeadBrief(
                        lead_type=lead.lead_type, requested_date=lead.requested_date
                    ),
                )
            )

        self._staff_alerts.alert(
            business,
            lead_alert(business.id, lead.id, lead.conversation_id),
            StaffAlertTexts(detailed=render, brief=render_brief),
        )
