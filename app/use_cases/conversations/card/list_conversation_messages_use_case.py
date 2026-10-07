from typed_time_provider import Microseconds, WallClock

from app.contracts.repositories.compliance_repositories import AuditLogRepoContract
from app.contracts.repositories.conversation_repositories import (
    ConversationRepoContract,
    MessageRepoContract,
)
from app.contracts.repositories.delivery_repositories import (
    OutboundMessageRepoContract,
)
from app.contracts.transformer_contract import TransformerContract
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.constants.compliance import AuditAction
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.domain.compliance import AuditLogEntryDocument
from app.schemas.domain.conversations import ConversationDocument, MessageDocument
from app.schemas.dto.access import BusinessAccessRequest
from app.schemas.dto.conversation_feed.conversation_views import (
    ConversationMessagesQuery,
    MessagePage,
    MessageView,
)
from app.schemas.exceptions.application_errors import NotFoundError
from app.schemas.typings.compliance.strings import (
    AuditEntityName,
    AuditEntityReference,
)
from app.schemas.typings.platform.constrained_strings import PageCursor
from app.use_cases.conversations.staff_reply_deliveries import with_staff_deliveries
from app.utilities.paging.keyset_paging import finish_page, read_slice

CONVERSATION_ENTITY: AuditEntityName = AuditEntityName("conversation")


class ListConversationMessagesUseCase(
    UseCaseContract[ConversationMessagesQuery, MessagePage]
):
    """
    Earlier messages of a conversation for its card: the keyset page
    before the cursor (the database reads only that page), returned oldest
    first so the cabinet puts them above what it shows. Reading a
    transcript is an operation on personal data: audited like the card.
    """

    def __init__(
        self,
        authorize_business_access: UseCaseContract[
            BusinessAccessRequest, BusinessDocument
        ],
        conversation_repo: ConversationRepoContract,
        message_repo: MessageRepoContract,
        message_transformer: TransformerContract[MessageDocument, MessageView],
        audit_log_repo: AuditLogRepoContract,
        wall_clock: WallClock[Microseconds],
        outbound_message_repo: OutboundMessageRepoContract,
    ) -> None:
        self._authorize_business_access: UseCaseContract[
            BusinessAccessRequest, BusinessDocument
        ] = authorize_business_access
        self._conversation_repo: ConversationRepoContract = conversation_repo
        self._message_repo: MessageRepoContract = message_repo
        self._message_transformer: TransformerContract[MessageDocument, MessageView] = (
            message_transformer
        )
        self._audit_log_repo: AuditLogRepoContract = audit_log_repo
        self._wall_clock: WallClock[Microseconds] = wall_clock
        self._outbound_message_repo: OutboundMessageRepoContract = outbound_message_repo

    def run(self, input_data: ConversationMessagesQuery) -> MessagePage:
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
        next_cursor: PageCursor | None
        newest_first, next_cursor = finish_page(
            self._message_repo.page_transcript(
                business.id, conversation.id, read_slice(input_data.page)
            ),
            input_data.page,
            sort_key=lambda message: int(message.created_at),
            item_id=lambda message: str(message.id),
        )
        now: Microseconds = self._wall_clock.now_unix()
        self._audit_log_repo.append(
            AuditLogEntryDocument(
                business_id=business.id,
                actor_id=input_data.user_id,
                action=AuditAction.VIEW,
                entity=CONVERSATION_ENTITY,
                entity_id=AuditEntityReference(str(conversation.id)),
                ip_address=input_data.client_ip_address,
                created_at=now,
                updated_at=now,
            )
        )
        return MessagePage(
            items=with_staff_deliveries(
                business.id,
                newest_first,
                [
                    self._message_transformer.transform(message)
                    for message in reversed(newest_first)
                ],
                self._outbound_message_repo,
            ),
            next_cursor=next_cursor,
        )
