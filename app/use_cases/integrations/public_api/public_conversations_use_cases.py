"""The public API's conversations: `GET /v1/public-api/conversations[/{id}]`."""

from typed_time_provider import Microseconds, WallClock

from app.contracts.integrations import PublicRecordReaderContract
from app.contracts.repositories.business_repositories import BusinessRepoContract
from app.contracts.repositories.compliance_repositories import AuditLogRepoContract
from app.contracts.repositories.conversation_repositories import (
    ConversationRepoContract,
)
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.constants.integrations import ApiKeyScope
from app.schemas.dto.listing_filters import ConversationFeedFilter
from app.schemas.dto.public_api.access import PublicConversationQuery, PublicListQuery
from app.schemas.dto.public_api.activity import PublicConversationDetail
from app.schemas.dto.public_api.pages import PublicConversationPage
from app.schemas.exceptions.application_errors import NotFoundError
from app.use_cases.integrations.api_key_records import require_scope
from app.use_cases.integrations.public_api.public_access import (
    API_CONVERSATION_ENTITY,
    key_business,
    record_public_read,
)
from app.utilities.paging.keyset_paging import finish_page, read_slice

UNKNOWN_CONVERSATION_MESSAGE: str = "Conversation not found."


class ListPublicConversationsUseCase(
    UseCaseContract[PublicListQuery, PublicConversationPage]
):
    """
    The key's business's conversations, the latest message first, one
    keyset page at a time (no test chats), without their messages. Needs
    `conversations:read`; audited.
    """

    def __init__(
        self,
        business_repo: BusinessRepoContract,
        conversation_repo: ConversationRepoContract,
        record_reader: PublicRecordReaderContract,
        audit_log_repo: AuditLogRepoContract,
        wall_clock: WallClock[Microseconds],
    ) -> None:
        self._business_repo: BusinessRepoContract = business_repo
        self._conversation_repo: ConversationRepoContract = conversation_repo
        self._record_reader: PublicRecordReaderContract = record_reader
        self._audit_log_repo: AuditLogRepoContract = audit_log_repo
        self._wall_clock: WallClock[Microseconds] = wall_clock

    def run(self, input_data: PublicListQuery) -> PublicConversationPage:
        require_scope(input_data.principal, ApiKeyScope.CONVERSATIONS_READ)
        business = key_business(self._business_repo, input_data.principal)
        conversations, next_cursor = finish_page(
            self._conversation_repo.page_feed(
                business.id, read_slice(input_data.page), ConversationFeedFilter()
            ),
            input_data.page,
            lambda conversation: int(conversation.last_message_at),
            lambda conversation: str(conversation.id),
        )
        items = self._record_reader.conversations(business, conversations)
        record_public_read(
            self._audit_log_repo,
            input_data.principal,
            API_CONVERSATION_ENTITY,
            len(items),
            self._wall_clock.now_unix(),
        )
        return PublicConversationPage(items=items, next_cursor=next_cursor)


class GetPublicConversationUseCase(
    UseCaseContract[PublicConversationQuery, PublicConversationDetail]
):
    """
    One conversation with its latest 100 messages, oldest first (the
    team's internal notes are never included). Needs `conversations:read`;
    audited.
    """

    def __init__(
        self,
        business_repo: BusinessRepoContract,
        record_reader: PublicRecordReaderContract,
        audit_log_repo: AuditLogRepoContract,
        wall_clock: WallClock[Microseconds],
    ) -> None:
        self._business_repo: BusinessRepoContract = business_repo
        self._record_reader: PublicRecordReaderContract = record_reader
        self._audit_log_repo: AuditLogRepoContract = audit_log_repo
        self._wall_clock: WallClock[Microseconds] = wall_clock

    def run(self, input_data: PublicConversationQuery) -> PublicConversationDetail:
        require_scope(input_data.principal, ApiKeyScope.CONVERSATIONS_READ)
        business = key_business(self._business_repo, input_data.principal)
        conversation = self._record_reader.conversation_detail(
            business, input_data.conversation_id
        )
        if conversation is None:
            raise NotFoundError(UNKNOWN_CONVERSATION_MESSAGE)

        record_public_read(
            self._audit_log_repo,
            input_data.principal,
            API_CONVERSATION_ENTITY,
            1,
            self._wall_clock.now_unix(),
        )
        return conversation
