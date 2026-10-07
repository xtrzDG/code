"""The team inbox's pages and counts, and the index each must use."""

from collections.abc import Callable
from dataclasses import dataclass
from typing import LiteralString

from base_pydantic_schemas import PersistentDocument

from app.adapters.storage.postgres.postgres_document_collection_adapter import (
    PostgresDocumentCollectionAdapter,
)
from app.clients.postgres.postgres_connection_pool_client import (
    PostgresConnectionPoolClient,
)
from app.repositories.conversation_repositories import ConversationRepository
from app.repositories.inbox_repositories import ConversationNoteRepository
from app.repositories.inbox_work_repository import InboxWorkRepository
from app.schemas.constants.channels import ChannelKind
from app.schemas.constants.inbox import InboxView
from app.schemas.domain.bookings import LeadDocument
from app.schemas.domain.conversation_notes import ConversationNoteDocument
from app.schemas.domain.conversations import ConversationDocument
from app.schemas.domain.handoffs import HandoffDocument
from app.schemas.dto.inbox.inbox_views import InboxViewFilter
from app.schemas.typings.conversations.prefixed_id import ConversationId
from app.schemas.typings.storage.constrained_strings import DocumentCollectionName
from app.schemas.typings.users.prefixed_id import UserId
from app.utilities.storage.document_tenancy import infer_collection_isolation
from app.utilities.storage.storage_scope_context import StorageScopeContext
from tests.storage.hot_path_rows import SeededTable
from tests.storage.list_query_plans import BUSINESS, FIRST_PAGE, LATER_PAGE
from tests.storage.list_query_rows import CONVERSATION, FLAG, LIST_TABLES
from tests.storage.storage_testing import build_fixed_wall_clock

VIEWER: UserId = UserId()
PAGE_OF_CONVERSATIONS: list[ConversationId] = [ConversationId() for _ in range(50)]
# A person is needed in one conversation of twenty, a request is open in one
# of fifteen; half of those waiting have somebody assigned.
AWAITS: LiteralString = "(n %% 20 = 0 or n %% 15 = 0)"
# A user id (a UUID v4 made from n mod 4) of four members.
MEMBER: LiteralString = (
    "'user_' || (substr(md5((n %% 4)::text), 1, 12) || '4' || "
    "substr(md5((n %% 4)::text), 14, 3) || 'a' || "
    "substr(md5((n %% 4)::text), 18, 15))::uuid"
)
INBOX_TABLES: tuple[SeededTable, ...] = (
    SeededTable(
        "conversations",
        "jsonb_build_object('contact_id', 'seeded_contact_' || (n %% 1000), "
        "'channel_user_id', 'tg_' || n, "
        "'status', case when n %% 20 = 0 then 'handoff' "
        "when n %% 3 = 0 then 'closed' else 'open' end, "
        "'channel', (array['telegram', 'whatsapp', 'web_chat'])[1 + n %% 3], "
        f"'is_sandbox', {FLAG}, 'has_open_request', n %% 15 = 0, "
        f"'awaits_team', {AWAITS}, "
        f"'assignee_user_id', case when {AWAITS} and n %% 2 = 0 then {MEMBER} end, "
        "'created_at', %(time)s + n * 1000, 'last_message_at', %(time)s + n * 2000)",
    ),
    SeededTable(
        "conversation_notes",
        f"jsonb_build_object('conversation_id', {CONVERSATION}, "
        f"'author_user_id', {MEMBER}, "
        "'created_at', %(time)s + n * 1000)",
    ),
    *(table for table in LIST_TABLES if table.name in {"leads", "handoffs"}),
)


class InboxRepositories:
    def __init__(
        self,
        connection_pool: PostgresConnectionPoolClient,
        storage_scope: StorageScopeContext,
    ) -> None:
        self._pool = connection_pool
        self._scope = storage_scope
        self.conversations = ConversationRepository(
            self._collection(ConversationDocument, "conversations")
        )
        self.notes = ConversationNoteRepository(
            self._collection(ConversationNoteDocument, "conversation_notes")
        )
        self.work = InboxWorkRepository(
            self._collection(HandoffDocument, "handoffs"),
            self._collection(LeadDocument, "leads"),
        )

    def _collection[StoredDocument: PersistentDocument](
        self, document_type: type[StoredDocument], name: str
    ) -> PostgresDocumentCollectionAdapter[StoredDocument]:
        return PostgresDocumentCollectionAdapter[StoredDocument](
            document_type=document_type,
            collection_name=DocumentCollectionName(name),
            connection_pool=self._pool,
            storage_scope=self._scope,
            wall_clock=build_fixed_wall_clock(),
            isolation=infer_collection_isolation(document_type),
        )


def view(name: InboxView, channel: ChannelKind | None = None) -> InboxViewFilter:
    return InboxViewFilter(view=name, viewer=VIEWER, channel=channel)


@dataclass(frozen=True)
class InboxPlanQuery:
    """A repository call of the inbox and the index its SQL must use."""

    name: str
    run: Callable[[InboxRepositories], object]
    table: str
    index: str


AWAITS_TEAM_INDEX: str = "conversations_doc_awaits_team_idx"
NOTES_INDEX: str = "conversation_notes_doc_conversation_idx"

INBOX_QUERIES: tuple[InboxPlanQuery, ...] = (
    InboxPlanQuery(
        "needs a person, first page",
        lambda r: r.conversations.page_inbox(
            BUSINESS, FIRST_PAGE, view(InboxView.NEEDS_PERSON)
        ),
        "conversations",
        "conversations_doc_status_last_message_at_idx",
    ),
    InboxPlanQuery(
        "open requests, a later page",
        lambda r: r.conversations.page_inbox(
            BUSINESS, LATER_PAGE, view(InboxView.REQUESTS)
        ),
        "conversations",
        "conversations_doc_open_request_idx",
    ),
    InboxPlanQuery(
        "mine, first page",
        lambda r: r.conversations.page_inbox(
            BUSINESS, FIRST_PAGE, view(InboxView.MINE)
        ),
        "conversations",
        AWAITS_TEAM_INDEX,
    ),
    InboxPlanQuery(
        "unassigned in one channel",
        lambda r: r.conversations.page_inbox(
            BUSINESS, FIRST_PAGE, view(InboxView.UNASSIGNED, ChannelKind.WHATSAPP)
        ),
        "conversations",
        AWAITS_TEAM_INDEX,
    ),
    InboxPlanQuery(
        "all, a later page",
        lambda r: r.conversations.page_inbox(BUSINESS, LATER_PAGE, view(InboxView.ALL)),
        "conversations",
        "conversations_doc_last_message_at_idx",
    ),
    InboxPlanQuery(
        "counts of the views",
        lambda r: r.conversations.count_inbox(BUSINESS, VIEWER),
        "conversations",
        AWAITS_TEAM_INDEX,
    ),
    InboxPlanQuery(
        "workload of each member",
        lambda r: r.conversations.count_awaiting_by_assignee(BUSINESS),
        "conversations",
        AWAITS_TEAM_INDEX,
    ),
    InboxPlanQuery(
        "notes of a conversation, newest first",
        lambda r: r.notes.page_by_conversation(BUSINESS, ConversationId(), FIRST_PAGE),
        "conversation_notes",
        NOTES_INDEX,
    ),
    InboxPlanQuery(
        "note counts of an inbox page",
        lambda r: r.notes.count_by_conversations(BUSINESS, PAGE_OF_CONVERSATIONS),
        "conversation_notes",
        NOTES_INDEX,
    ),
    InboxPlanQuery(
        "open handoffs of an inbox page",
        lambda r: r.work.latest_open_handoffs(BUSINESS, PAGE_OF_CONVERSATIONS),
        "handoffs",
        "handoffs_doc_conversation_idx",
    ),
    InboxPlanQuery(
        "open requests of an inbox page",
        lambda r: r.work.latest_open_requests(BUSINESS, PAGE_OF_CONVERSATIONS),
        "leads",
        "leads_doc_conversation_idx",
    ),
    InboxPlanQuery(
        "whether a conversation has an open request",
        lambda r: r.work.has_open_request(BUSINESS, ConversationId()),
        "leads",
        "leads_doc_conversation_idx",
    ),
)
