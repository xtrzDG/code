from typed_time_provider import Microseconds, WallClock

from app.contracts.repositories.booking_repositories import (
    BookingRepoContract,
    LeadRepoContract,
)
from app.contracts.repositories.compliance_repositories import AuditLogRepoContract
from app.contracts.repositories.conversation_repositories import (
    ContactRepoContract,
    ConversationRepoContract,
)
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.constants.compliance import AuditAction
from app.schemas.constants.users import BusinessMemberRole
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.domain.compliance import AuditLogEntryDocument
from app.schemas.domain.contacts import ContactDocument
from app.schemas.dto.access import BusinessAccessRequest
from app.schemas.dto.contacts import (
    ContactActivity,
    ContactBookingView,
    ContactConversationView,
    ContactDetailView,
    ContactLeadView,
    ContactQuery,
)
from app.schemas.exceptions.application_errors import NotFoundError
from app.schemas.typings.compliance.strings import (
    AuditEntityName,
    AuditEntityReference,
)
from app.use_cases.contacts.contact_summaries import (
    collect_contact_activity,
    summarize_contact,
)


class GetContactUseCase(UseCaseContract[ContactQuery, ContactDetailView]):
    """
    Owner opens one customer: who they are, their conversations, bookings
    and leads (test chats left out), newest first. An erased customer is
    shown without personal data. The view is audited (VIEW of the contact).
    """

    def __init__(
        self,
        authorize_business_access: UseCaseContract[
            BusinessAccessRequest,
            BusinessDocument,
        ],
        contact_repo: ContactRepoContract,
        conversation_repo: ConversationRepoContract,
        booking_repo: BookingRepoContract,
        lead_repo: LeadRepoContract,
        audit_log_repo: AuditLogRepoContract,
        wall_clock: WallClock[Microseconds],
    ) -> None:
        self._authorize_business_access: UseCaseContract[
            BusinessAccessRequest,
            BusinessDocument,
        ] = authorize_business_access
        self._contact_repo: ContactRepoContract = contact_repo
        self._conversation_repo: ConversationRepoContract = conversation_repo
        self._booking_repo: BookingRepoContract = booking_repo
        self._lead_repo: LeadRepoContract = lead_repo
        self._audit_log_repo: AuditLogRepoContract = audit_log_repo
        self._wall_clock: WallClock[Microseconds] = wall_clock

    def run(self, input_data: ContactQuery) -> ContactDetailView:
        business: BusinessDocument = self._authorize_business_access.run(
            BusinessAccessRequest(
                user_id=input_data.user_id,
                business_id=input_data.business_id,
                required_role=BusinessMemberRole.OWNER,
            )
        )
        contact: ContactDocument | None = self._contact_repo.get(
            business.id,
            input_data.contact_id,
        )
        if contact is None:
            raise NotFoundError(f"Contact {input_data.contact_id} was not found.")

        activity: ContactActivity = collect_contact_activity(
            business.id,
            self._conversation_repo,
            self._booking_repo,
            self._lead_repo,
        ).get(contact.id, ContactActivity())
        now: Microseconds = self._wall_clock.now_unix()
        self._audit_log_repo.append(
            AuditLogEntryDocument(
                business_id=business.id,
                actor_id=input_data.user_id,
                action=AuditAction.VIEW,
                entity=AuditEntityName("contact"),
                entity_id=AuditEntityReference(str(contact.id)),
                ip_address=input_data.client_ip_address,
                created_at=now,
                updated_at=now,
            )
        )
        return ContactDetailView(
            contact=summarize_contact(contact, activity),
            conversations=[
                ContactConversationView(
                    id=conversation.id,
                    channel=conversation.channel,
                    status=conversation.status,
                    started_at=conversation.created_at,
                    last_message_at=conversation.last_message_at,
                )
                for conversation in sorted(
                    activity.conversations,
                    key=lambda conversation: conversation.last_message_at,
                    reverse=True,
                )
            ],
            bookings=[
                ContactBookingView(
                    id=booking.id,
                    starts_at=booking.starts_at,
                    status=booking.status,
                    created_at=booking.created_at,
                )
                for booking in sorted(
                    activity.bookings,
                    key=lambda booking: booking.starts_at,
                    reverse=True,
                )
            ],
            leads=[
                ContactLeadView(
                    id=lead.id,
                    status=lead.status,
                    created_at=lead.created_at,
                )
                for lead in sorted(
                    activity.leads,
                    key=lambda lead: lead.created_at,
                    reverse=True,
                )
            ],
        )
