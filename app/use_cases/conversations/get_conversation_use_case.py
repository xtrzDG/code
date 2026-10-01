from zoneinfo import ZoneInfo

from typed_time_provider import Microseconds, WallClock

from app.contracts.repositories import (
    AuditLogRepoContract,
    BookingRepoContract,
    CallRepoContract,
    ChannelRepoContract,
    ContactRepoContract,
    ConversationRepoContract,
    HandoffRepoContract,
    LeadRepoContract,
    MessageRepoContract,
    ResourceRepoContract,
)
from app.contracts.transformer_contract import TransformerContract
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.constants.compliance import AuditAction
from app.schemas.domain.bookings import BookingDocument
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.domain.compliance import AuditLogEntryDocument
from app.schemas.domain.contacts import ContactDocument
from app.schemas.domain.conversations import (
    CallDocument,
    ConversationDocument,
    MessageDocument,
)
from app.schemas.domain.resources import ResourceDocument
from app.schemas.dto.access import BusinessAccessRequest
from app.schemas.dto.bookings import BookingView
from app.schemas.dto.conversation_feed import (
    CallView,
    ConversationDetailView,
    ConversationQuery,
    ConversationSummaryView,
    ConversationViewSource,
    MessageView,
)
from app.schemas.exceptions.application_errors import NotFoundError
from app.schemas.typings.bookings.prefixed_id import ResourceId
from app.schemas.typings.compliance.strings import (
    AuditEntityName,
    AuditEntityReference,
)
from app.schemas.typings.contacts.prefixed_id import ContactId
from app.use_cases.conversations.staff_reply_support import (
    assess_conversation_reply,
)
from app.use_cases.handoffs.handoff_views import build_handoff_list_item
from app.use_cases.leads.lead_views import build_lead_list_item
from app.utilities.scheduling.booking_views import build_booking_view
from app.utilities.scheduling.zoned_time import load_time_zone

CONVERSATION_ENTITY: AuditEntityName = AuditEntityName("conversation")
CALL_ENTITY: AuditEntityName = AuditEntityName("call")


class GetConversationUseCase(
    UseCaseContract[ConversationQuery, ConversationDetailView]
):
    """
    Conversation card for owners and staff: the transcript with every tool
    call, model, tokens and cost, the phone calls of the conversation with
    their transcripts, outcomes and recordings, the bookings, leads and
    handoffs made in it, and whether staff can write to the customer now
    (concept section 8). Reading a conversation is an operation on personal
    data, so each view is written to the audit log, one entry per call
    shown as well (concept section 10).
    """

    def __init__(
        self,
        authorize_business_access: UseCaseContract[
            BusinessAccessRequest, BusinessDocument
        ],
        conversation_repo: ConversationRepoContract,
        contact_repo: ContactRepoContract,
        message_repo: MessageRepoContract,
        audit_log_repo: AuditLogRepoContract,
        summary_transformer: TransformerContract[
            ConversationViewSource, ConversationSummaryView
        ],
        message_transformer: TransformerContract[MessageDocument, MessageView],
        wall_clock: WallClock[Microseconds],
        call_repo: CallRepoContract,
        call_transformer: TransformerContract[CallDocument, CallView],
        booking_repo: BookingRepoContract,
        lead_repo: LeadRepoContract,
        handoff_repo: HandoffRepoContract,
        resource_repo: ResourceRepoContract,
        channel_repo: ChannelRepoContract,
    ) -> None:
        self._authorize_business_access: UseCaseContract[
            BusinessAccessRequest, BusinessDocument
        ] = authorize_business_access
        self._conversation_repo: ConversationRepoContract = conversation_repo
        self._contact_repo: ContactRepoContract = contact_repo
        self._message_repo: MessageRepoContract = message_repo
        self._audit_log_repo: AuditLogRepoContract = audit_log_repo
        self._summary_transformer: TransformerContract[
            ConversationViewSource, ConversationSummaryView
        ] = summary_transformer
        self._message_transformer: TransformerContract[MessageDocument, MessageView] = (
            message_transformer
        )
        self._wall_clock: WallClock[Microseconds] = wall_clock
        self._call_repo: CallRepoContract = call_repo
        self._call_transformer: TransformerContract[CallDocument, CallView] = (
            call_transformer
        )
        self._booking_repo: BookingRepoContract = booking_repo
        self._lead_repo: LeadRepoContract = lead_repo
        self._handoff_repo: HandoffRepoContract = handoff_repo
        self._resource_repo: ResourceRepoContract = resource_repo
        self._channel_repo: ChannelRepoContract = channel_repo

    def run(self, input_data: ConversationQuery) -> ConversationDetailView:
        business: BusinessDocument = self._authorize_business_access.run(
            BusinessAccessRequest(
                user_id=input_data.user_id,
                business_id=input_data.business_id,
            )
        )
        conversation: ConversationDocument | None = self._conversation_repo.get(
            business.id, input_data.conversation_id
        )
        if conversation is None:
            raise NotFoundError(
                f"Conversation {input_data.conversation_id} was not found."
            )

        messages: list[MessageDocument] = self._message_repo.list_by_conversation(
            business.id, conversation.id
        )
        calls: list[CallDocument] = sorted(
            (
                call
                for call in self._call_repo.list_by_business(business.id)
                if call.conversation_id == conversation.id
            ),
            key=lambda call: call.started_at,
        )
        now: Microseconds = self._wall_clock.now_unix()
        viewed: list[tuple[AuditEntityName, str]] = [
            (CONVERSATION_ENTITY, str(conversation.id)),
            *((CALL_ENTITY, str(call.id)) for call in calls),
        ]
        for entity, entity_id in viewed:
            self._audit_log_repo.append(
                AuditLogEntryDocument(
                    business_id=business.id,
                    actor_id=input_data.user_id,
                    action=AuditAction.VIEW,
                    entity=entity,
                    entity_id=AuditEntityReference(entity_id),
                    ip_address=input_data.client_ip_address,
                    created_at=now,
                    updated_at=now,
                )
            )
        contact: ContactDocument | None = self._contact_repo.get(
            business.id, conversation.contact_id
        )
        return ConversationDetailView(
            conversation=self._summary_transformer.transform(
                ConversationViewSource(
                    conversation=conversation,
                    contact=contact,
                    messages=messages,
                )
            ),
            messages=[
                self._message_transformer.transform(message) for message in messages
            ],
            calls=[self._call_transformer.transform(call) for call in calls],
            bookings=self._bookings(business, conversation, contact),
            leads=[
                build_lead_list_item(
                    lead, self._contact_of(business, lead.contact_id, contact)
                )
                for lead in self._lead_repo.list_by_business(business.id)
                if lead.conversation_id == conversation.id
            ],
            handoffs=[
                build_handoff_list_item(
                    handoff, self._contact_of(business, handoff.contact_id, contact)
                )
                for handoff in self._handoff_repo.list_by_business(business.id)
                if handoff.conversation_id == conversation.id
            ],
            reply=assess_conversation_reply(
                conversation,
                self._conversation_repo,
                self._message_repo,
                self._channel_repo,
                now,
            ),
        )

    def _bookings(
        self,
        business: BusinessDocument,
        conversation: ConversationDocument,
        contact: ContactDocument | None,
    ) -> list[BookingView]:
        """Bookings made in the conversation, by start time."""

        bookings: list[BookingDocument] = [
            booking
            for booking in self._booking_repo.list_by_business(business.id)
            if booking.conversation_id == conversation.id
        ]
        if not bookings:
            return []

        resources: dict[ResourceId, ResourceDocument] = {
            resource.id: resource
            for resource in self._resource_repo.list_by_business(business.id)
        }
        zone: ZoneInfo = load_time_zone(business.timezone)
        return [
            build_booking_view(
                booking,
                business.timezone,
                zone,
                resources.get(booking.resource_id),
                self._contact_of(business, booking.contact_id, contact),
            )
            for booking in sorted(bookings, key=lambda booking: int(booking.starts_at))
        ]

    def _contact_of(
        self,
        business: BusinessDocument,
        contact_id: ContactId,
        conversation_contact: ContactDocument | None,
    ) -> ContactDocument | None:
        """The conversation's contact, or another one an item names."""

        if conversation_contact is not None and conversation_contact.id == contact_id:
            return conversation_contact

        return self._contact_repo.get(business.id, contact_id)
