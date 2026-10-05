"""The keyset pages and counts of the cabinet, and the index each must use."""

from collections.abc import Callable
from dataclasses import dataclass

from base_pydantic_schemas import PersistentDocument
from typed_time_provider import Microseconds

from app.adapters.storage.postgres.postgres_document_collection_adapter import (
    PostgresDocumentCollectionAdapter,
)
from app.clients.postgres.postgres_connection_pool_client import (
    PostgresConnectionPoolClient,
)
from app.repositories.booking_repositories import (
    BookingRepository,
    HandoffRepository,
    LeadRepository,
    UnansweredQuestionRepository,
)
from app.repositories.compliance_repositories import AuditLogRepository
from app.repositories.contact_activity_repository import ContactActivityRepository
from app.repositories.conversation_repositories import (
    ContactRepository,
    ConversationRepository,
    MessageRepository,
)
from app.repositories.knowledge_repositories import KnowledgeItemRepository
from app.schemas.constants.bookings import BookingOrder, BookingStatus
from app.schemas.constants.channels import ChannelKind
from app.schemas.constants.handoffs import HandoffUrgency
from app.schemas.domain.bookings import BookingDocument, LeadDocument
from app.schemas.domain.compliance import AuditLogEntryDocument
from app.schemas.domain.contacts import ContactDocument
from app.schemas.domain.conversations import ConversationDocument, MessageDocument
from app.schemas.domain.handoffs import HandoffDocument, UnansweredQuestionDocument
from app.schemas.domain.knowledge import KnowledgeItemDocument
from app.schemas.dto.listing_filters import (
    AuditLogFilter,
    BookingListFilter,
    ConversationFeedFilter,
    HandoffListFilter,
)
from app.schemas.dto.operations.activity_counts import ActivityPeriod
from app.schemas.dto.paging import KeysetPosition, KeysetSlice
from app.schemas.typings.bookings.constrained_integers import BookingSearchBoundSeconds
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.conversations.prefixed_id import ConversationId
from app.schemas.typings.platform.constrained_integers import KeysetReadLimit
from app.schemas.typings.platform.integers import ListSortValue
from app.schemas.typings.platform.strings import ListItemKey
from app.schemas.typings.storage.constrained_strings import DocumentCollectionName
from app.utilities.storage.document_tenancy import infer_collection_isolation
from app.utilities.storage.storage_scope_context import StorageScopeContext
from tests.storage.hot_path_rows import BASE_TIME
from tests.storage.list_query_rows import LIST_BUSINESS_COUNT
from tests.storage.storage_testing import build_fixed_wall_clock

LIST_BUSINESS_IDS: list[BusinessId] = [BusinessId() for _ in range(LIST_BUSINESS_COUNT)]
BUSINESS: BusinessId = LIST_BUSINESS_IDS[0]
FIRST_PAGE = KeysetSlice(limit=KeysetReadLimit(51))
LATER_PAGE = KeysetSlice(
    after=KeysetPosition(
        sort_values=(ListSortValue(BASE_TIME + 9_000_000),),
        item_key=ListItemKey("seeded_4520"),
    ),
    limit=KeysetReadLimit(51),
)
START = Microseconds(BASE_TIME + 2_000_000)
END = Microseconds(BASE_TIME + 5_000_000)
# The last week of a long history: the last twentieth of the rows.
RECENT = Microseconds(BASE_TIME + 28_500_000)
PERIOD = ActivityPeriod(
    start=START,
    end=END,
    segment_starts=(START, Microseconds(BASE_TIME + 3_000_000)),
)


class ListRepositories:
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
        self.messages = MessageRepository(self._collection(MessageDocument, "messages"))
        self.bookings = BookingRepository(self._collection(BookingDocument, "bookings"))
        self.leads = LeadRepository(self._collection(LeadDocument, "leads"))
        self.handoffs = HandoffRepository(self._collection(HandoffDocument, "handoffs"))
        self.questions = UnansweredQuestionRepository(
            self._collection(UnansweredQuestionDocument, "unanswered_questions")
        )
        self.audit = AuditLogRepository(
            self._collection(AuditLogEntryDocument, "audit_log_entries")
        )
        self.contacts = ContactRepository(self._collection(ContactDocument, "contacts"))
        self.knowledge = KnowledgeItemRepository(
            self._collection(KnowledgeItemDocument, "knowledge_items")
        )
        self.contact_activity = ContactActivityRepository(
            self._collection(ConversationDocument, "conversations"),
            self._collection(BookingDocument, "bookings"),
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


@dataclass(frozen=True)
class ListQuery:
    """
    A repository call of a list or count and the index its SQL must use
    (or an equally selective one the planner may prefer, `alternatives`);
    none of `table` and `also_tables` may be read sequentially.
    """

    name: str
    run: Callable[[ListRepositories], object]
    table: str
    index: str
    alternatives: tuple[str, ...] = ()
    also_tables: tuple[str, ...] = ()


LIST_QUERIES: tuple[ListQuery, ...] = (
    ListQuery(
        "feed, first page",
        lambda r: r.conversations.page_feed(
            BUSINESS, FIRST_PAGE, ConversationFeedFilter()
        ),
        "conversations",
        "conversations_doc_last_message_at_idx",
    ),
    ListQuery(
        "feed, a later page of one channel",
        lambda r: r.conversations.page_feed(
            BUSINESS,
            LATER_PAGE,
            ConversationFeedFilter(channel=ChannelKind.TELEGRAM),
        ),
        "conversations",
        "conversations_doc_last_message_at_idx",
    ),
    ListQuery(
        "earlier messages of a transcript",
        lambda r: r.messages.page_transcript(BUSINESS, ConversationId(), LATER_PAGE),
        "messages",
        "messages_doc_conversation_idx",
    ),
    ListQuery(
        "upcoming bookings",
        lambda r: r.bookings.page_by_business(
            BUSINESS,
            FIRST_PAGE,
            # The future: the last tenth of the seeded bookings.
            BookingListFilter(starts_from=BookingSearchBoundSeconds(1_806_200_000)),
        ),
        "bookings",
        "bookings_doc_starts_at_idx",
    ),
    ListQuery(
        "pending bookings, latest first",
        lambda r: r.bookings.page_by_business(
            BUSINESS,
            FIRST_PAGE,
            BookingListFilter(
                status=BookingStatus.PENDING, order=BookingOrder.LATEST_FIRST
            ),
        ),
        "bookings",
        "bookings_doc_status_starts_at_idx",
    ),
    ListQuery(
        "bookings not over (availability)",
        lambda r: r.bookings.list_ending_after(
            BUSINESS, BookingSearchBoundSeconds(1_806_200_000)
        ),
        "bookings",
        "bookings_doc_ends_at_idx",
    ),
    ListQuery(
        "leads, newest first",
        lambda r: r.leads.page_by_business(BUSINESS, LATER_PAGE, None, False),
        "leads",
        "leads_doc_created_at_idx",
    ),
    ListQuery(
        "open critical handoffs",
        lambda r: r.handoffs.page_open(
            BUSINESS, HandoffUrgency.CRITICAL, FIRST_PAGE, HandoffListFilter()
        ),
        "handoffs",
        "handoffs_doc_queue_idx",
    ),
    ListQuery(
        "resolved handoffs",
        lambda r: r.handoffs.page_resolved(BUSINESS, LATER_PAGE, False),
        "handoffs",
        "handoffs_doc_resolved_at_idx",
    ),
    ListQuery(
        "open unanswered questions",
        lambda r: r.questions.page_by_rank(BUSINESS, FIRST_PAGE, False, False),
        "unanswered_questions",
        "unanswered_questions_doc_open_rank_idx",
    ),
    ListQuery(
        "audit log",
        lambda r: r.audit.page_by_business(BUSINESS, LATER_PAGE, AuditLogFilter()),
        "audit_log_entries",
        "audit_log_entries_doc_created_at_idx",
    ),
    ListQuery(
        "dashboard: conversations by channel and language",
        lambda r: r.conversations.count_started_by_mix(BUSINESS, START, END),
        "conversations",
        "conversations_doc_created_at_idx",
    ),
    ListQuery(
        "dashboard: customer messages of a period",
        lambda r: r.messages.count_customer_messages(BUSINESS, START, END),
        "messages",
        "messages_doc_author_created_at_idx",
    ),
    ListQuery(
        "dashboard: bookings made per day",
        lambda r: r.bookings.count_made(BUSINESS, PERIOD),
        "bookings",
        "bookings_doc_created_at_idx",
    ),
    ListQuery(
        "dashboard: what the bookings made per day are worth",
        lambda r: r.bookings.sum_value_made(BUSINESS, PERIOD),
        "bookings",
        "bookings_doc_created_at_idx",
    ),
    ListQuery(
        "admin: model spend per conversation",
        lambda r: r.messages.sum_cost_by_conversation(BUSINESS, START, END),
        "messages",
        "messages_doc_created_at_idx",
    ),
    ListQuery(
        "admin: what the reply guard did (GUARD_SPIKE)",
        lambda r: r.messages.count_guard_activity(BUSINESS, RECENT),
        "messages",
        "messages_doc_created_at_idx",
        ("messages_doc_reply_latency_idx", "messages_doc_author_created_at_idx"),
    ),
    ListQuery(
        "admin: recent handoffs",
        lambda r: r.handoffs.count_made_since(BUSINESS, RECENT),
        "handoffs",
        "handoffs_doc_created_at_idx",
        # A short recent window: the platform alerts' index (1093) of the
        # creation time alone reads as few rows.
        ("handoffs_doc_created_at_platform_idx",),
    ),
    ListQuery(
        "newest written message of each conversation of a feed page",
        lambda r: r.messages.find_latest_written(
            BUSINESS, [ConversationId() for _ in range(50)]
        ),
        "messages",
        "messages_doc_conversation_idx",
    ),
    ListQuery(
        "message counts of a feed page",
        lambda r: r.messages.tally_conversations(
            BUSINESS, [ConversationId() for _ in range(50)]
        ),
        "messages",
        "messages_doc_conversation_idx",
    ),
)
