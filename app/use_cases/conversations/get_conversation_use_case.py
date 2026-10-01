from typed_time_provider import Microseconds, WallClock

from app.contracts.repositories import (
    AuditLogRepoContract,
    CallRepoContract,
    ContactRepoContract,
    ConversationRepoContract,
    MessageRepoContract,
)
from app.contracts.transformer_contract import TransformerContract
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.constants.compliance import AuditAction
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.domain.compliance import AuditLogEntryDocument
from app.schemas.domain.conversations import (
    CallDocument,
    ConversationDocument,
    MessageDocument,
)
from app.schemas.dto.access import BusinessAccessRequest
from app.schemas.dto.conversation_feed import (
    CallView,
    ConversationDetailView,
    ConversationQuery,
    ConversationSummaryView,
    ConversationViewSource,
    MessageView,
)
from app.schemas.exceptions.application_errors import NotFoundError
from app.schemas.typings.compliance.strings import (
    AuditEntityName,
    AuditEntityReference,
)

CONVERSATION_ENTITY: AuditEntityName = AuditEntityName("conversation")
CALL_ENTITY: AuditEntityName = AuditEntityName("call")


class GetConversationUseCase(
    UseCaseContract[ConversationQuery, ConversationDetailView]
):
    """
    Conversation card for owners and staff: the transcript with every tool
    call, model, tokens and cost, and the phone calls of the conversation
    with their transcripts, outcomes and recordings (concept section 8).
    Reading a conversation is an operation on personal data, so each view
    is written to the audit log, one entry per call shown as well (concept
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
        return ConversationDetailView(
            conversation=self._summary_transformer.transform(
                ConversationViewSource(
                    conversation=conversation,
                    contact=self._contact_repo.get(
                        business.id, conversation.contact_id
                    ),
                    messages=messages,
                )
            ),
            messages=[
                self._message_transformer.transform(message) for message in messages
            ],
            calls=[self._call_transformer.transform(call) for call in calls],
        )
