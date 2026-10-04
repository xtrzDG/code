from typed_time_provider import Microseconds, WallClock

from app.contracts.repositories.booking_repositories import (
    BookingRepoContract,
    HandoffRepoContract,
    LeadRepoContract,
)
from app.contracts.repositories.business_repositories import ChannelRepoContract
from app.contracts.repositories.compliance_repositories import AuditLogRepoContract
from app.contracts.repositories.conversation_repositories import (
    CallRepoContract,
    ContactRepoContract,
    ConversationRepoContract,
    MessageRepoContract,
)
from app.contracts.repositories.delivery_repositories import (
    OutboundMessageRepoContract,
)
from app.contracts.repositories.knowledge_repositories import ResourceRepoContract
from app.contracts.transformer_contract import TransformerContract
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.constants.compliance import AuditAction
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.domain.compliance import AuditLogEntryDocument
from app.schemas.domain.contacts import ContactDocument
from app.schemas.domain.conversations import (
    CallDocument,
    ConversationDocument,
    MessageDocument,
)
from app.schemas.dto.access import BusinessAccessRequest
from app.schemas.dto.conversation_feed.conversation_views import (
    CallView,
    ConversationDetailView,
    ConversationQuery,
    ConversationSummaryView,
    ConversationViewSource,
    MessageView,
)
from app.schemas.dto.paging import PageRequest
from app.schemas.exceptions.application_errors import NotFoundError
from app.schemas.typings.compliance.strings import (
    AuditEntityName,
    AuditEntityReference,
)
from app.schemas.typings.platform.constrained_integers import PageSize
from app.schemas.typings.platform.constrained_strings import PageCursor
from app.use_cases.conversations.card.conversation_links import (
    ConversationLinks,
    collect_conversation_links,
)
from app.use_cases.conversations.feed.conversation_rows import build_view_sources
from app.use_cases.conversations.staff_reply_deliveries import with_staff_deliveries
from app.use_cases.conversations.staff_reply_support import (
    assess_conversation_reply,
)
from app.use_cases.shared.assignment_views import build_assignment_view
from app.utilities.paging.keyset_paging import finish_page, read_slice

CONVERSATION_ENTITY: AuditEntityName = AuditEntityName("conversation")
CALL_ENTITY: AuditEntityName = AuditEntityName("call")
# The card shows the newest messages; earlier ones come page by page.
CARD_TRANSCRIPT: PageRequest = PageRequest(size=PageSize(100))


class GetConversationUseCase(
    UseCaseContract[ConversationQuery, ConversationDetailView]
):
    """
    Conversation card for owners and staff: the newest 100 messages of the
    transcript (a keyset page; `ListConversationMessagesUseCase` pages back)
    with every tool call, model, tokens and cost, the usage of the whole
    conversation, the phone calls of the conversation with
    their transcripts, outcomes and recordings, the bookings, leads and
    handoffs made in it, whether staff can write to the customer now
    (concept section 8), how each staff reply travels to the customer, and
    who of the team is assigned to it. Reading a
    conversation is an operation on personal data, so each view is
    written to the audit log, one entry per call shown as well (concept
    section 10).
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
        outbound_message_repo: OutboundMessageRepoContract,
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
        self._outbound_message_repo: OutboundMessageRepoContract = outbound_message_repo

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

        newest_first: list[MessageDocument]
        earlier_cursor: PageCursor | None
        newest_first, earlier_cursor = finish_page(
            self._message_repo.page_transcript(
                business.id, conversation.id, read_slice(CARD_TRANSCRIPT)
            ),
            CARD_TRANSCRIPT,
            sort_key=lambda message: int(message.created_at),
            item_id=lambda message: str(message.id),
        )
        calls: list[CallDocument] = self._call_repo.list_by_conversation(
            business.id, conversation.id
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
        links: ConversationLinks = collect_conversation_links(
            business,
            conversation.id,
            contact,
            self._booking_repo,
            self._lead_repo,
            self._handoff_repo,
            self._resource_repo,
            self._contact_repo,
        )
        return ConversationDetailView(
            conversation=self._summary_transformer.transform(
                build_view_sources(
                    business.id,
                    [conversation],
                    self._contact_repo,
                    self._message_repo,
                    {} if contact is None else {contact.id: contact},
                )[0]
            ),
            messages=with_staff_deliveries(
                business.id,
                newest_first,
                [
                    self._message_transformer.transform(message)
                    for message in reversed(newest_first)
                ],
                self._outbound_message_repo,
            ),
            earlier_messages_cursor=earlier_cursor,
            usage=self._message_repo.sum_usage(business.id, conversation.id),
            calls=[self._call_transformer.transform(call) for call in calls],
            bookings=links.bookings,
            leads=links.leads,
            handoffs=links.handoffs,
            reply=assess_conversation_reply(
                conversation,
                self._conversation_repo,
                self._message_repo,
                self._channel_repo,
                now,
            ),
            assignment=build_assignment_view(conversation),
        )
