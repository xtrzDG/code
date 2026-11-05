"""
The reads and deletes of the retention purge over the records of a
business: keyset batches on existing indexes (conversations by their last
message, leads and handoffs by creation, bookings by the visit's end) and
range deletes the store runs in transactions of at most 1,000 rows.
"""

from collections.abc import Callable

from typed_time_provider import Microseconds

from app.contracts.document_store import DocumentCollectionAdapterContract
from app.contracts.repositories.retention_repositories import (
    ExpiredLlmTurnRepoContract,
    ExpiredMessageRepoContract,
    ExpiredMissedCallRepoContract,
    ExpiringRecordRepoContract,
    QuietConversationRepoContract,
)
from app.repositories.business_scoped_repository import BusinessScopedRepository
from app.repositories.conversation_lookup_fields import (
    CONVERSATION_ID_FIELD,
    CREATED_AT_FIELD,
    LAST_MESSAGE_AT_FIELD,
    SEQUENCE_NUMBER_FIELD,
)
from app.repositories.document_queries import field_equals, of_business, time_range
from app.schemas.domain.bookings import BookingDocument, LeadDocument
from app.schemas.domain.conversations import (
    ConversationDocument,
    LlmTurnDocument,
    MessageDocument,
)
from app.schemas.domain.handoffs import HandoffDocument
from app.schemas.domain.missed_calls import MissedCallDocument
from app.schemas.dto.paging import KeysetPosition, KeysetSlice
from app.schemas.dto.retention import RetentionWindow
from app.schemas.dto.storage_queries import DocumentFieldRange, DocumentFilter
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.conversations.prefixed_id import ConversationId
from app.schemas.typings.platform.constrained_integers import KeysetReadLimit
from app.schemas.typings.platform.integers import ListSortValue
from app.schemas.typings.platform.strings import ListItemKey
from app.schemas.typings.privacy.constrained_integers import RetentionBatchSize
from app.schemas.typings.storage.constrained_integers import DocumentCount
from app.schemas.typings.storage.constrained_strings import DocumentFieldPath
from app.schemas.typings.storage.integers import DocumentFieldInteger

ENDS_AT_FIELD: DocumentFieldPath = DocumentFieldPath("ends_at")
MICROSECONDS_PER_SECOND: int = 1_000_000


class ExpiringRecordRepository[
    Record: (
        ConversationDocument,
        LeadDocument,
        HandoffDocument,
        BookingDocument,
    )
](BusinessScopedRepository[Record], ExpiringRecordRepoContract[Record]):
    """
    Keyset batches of a business's records by one INTEGER timestamp field
    (`_field`, in microseconds, or in seconds with `_microseconds_per_unit`
    1,000,000), ties in first-write order, so changing a record never moves
    it within the walk.
    """

    _field: DocumentFieldPath = CREATED_AT_FIELD
    _microseconds_per_unit: int = 1

    def page_in(
        self,
        business_id: BusinessId,
        window: RetentionWindow,
        after: Record | None,
        size: RetentionBatchSize,
    ) -> list[Record]:
        return self._page_in_business(
            business_id,
            [self._field],
            KeysetSlice(
                after=None if after is None else self._position(after),
                limit=KeysetReadLimit(int(size)),
            ),
            where=DocumentFilter(ranges=(self._range(window),)),
            is_descending=False,
        )

    def change(
        self,
        record: Record,
        change: Callable[[Record], Record | None],
    ) -> Record | None:
        return self._modify_in_business(record.business_id, str(record.id), change)

    def _range(self, window: RetentionWindow) -> DocumentFieldRange:
        """The window in the field's own unit."""

        unit: int = self._microseconds_per_unit
        return DocumentFieldRange(
            field=self._field,
            lower=(
                None
                if window.since is None
                else DocumentFieldInteger(int(window.since) // unit)
            ),
            upper=DocumentFieldInteger(int(window.before) // unit),
        )

    def _position(self, record: Record) -> KeysetPosition:
        return KeysetPosition(
            sort_values=(ListSortValue(self._sort_value(record)),),
            item_key=ListItemKey(str(record.id)),
        )

    def _sort_value(self, record: Record) -> int:
        return int(record.created_at)


class QuietConversationRepository(
    ExpiringRecordRepository[ConversationDocument], QuietConversationRepoContract
):
    """Conversations by their last message (1010's index)."""

    _field = LAST_MESSAGE_AT_FIELD

    def page_quiet_in(
        self,
        business_id: BusinessId,
        window: RetentionWindow,
        after: ConversationDocument | None,
        size: RetentionBatchSize,
    ) -> list[ConversationDocument]:
        return self.page_in(business_id, window, after, size)

    def _sort_value(self, record: ConversationDocument) -> int:
        return int(record.last_message_at)


class ExpiringLeadRepository(ExpiringRecordRepository[LeadDocument]):
    """Leads by when they were made (1042's index)."""


class ExpiringHandoffRepository(ExpiringRecordRepository[HandoffDocument]):
    """Handoffs by when they were made (1042's index)."""


class ExpiringBookingRepository(ExpiringRecordRepository[BookingDocument]):
    """Bookings by when the visit ends (in seconds; 1042's index)."""

    _field = ENDS_AT_FIELD
    _microseconds_per_unit = MICROSECONDS_PER_SECOND

    def _sort_value(self, record: BookingDocument) -> int:
        return int(record.ends_at)


class ExpiredMessageRepository(
    BusinessScopedRepository[MessageDocument], ExpiredMessageRepoContract
):
    """Messages by when they were written (1042's index)."""

    def delete_created_before(
        self, business_id: BusinessId, cutoff: Microseconds
    ) -> DocumentCount:
        return self._collection.delete_by_range(
            time_range(CREATED_AT_FIELD, None, cutoff), (of_business(business_id),)
        )


class ExpiredMissedCallRepository(
    BusinessScopedRepository[MissedCallDocument], ExpiredMissedCallRepoContract
):
    """Missed calls by when they were noted (1051's index)."""

    def delete_created_before(
        self, business_id: BusinessId, cutoff: Microseconds
    ) -> DocumentCount:
        return self._collection.delete_by_range(
            time_range(CREATED_AT_FIELD, None, cutoff), (of_business(business_id),)
        )


class ExpiredLlmTurnRepository(ExpiredLlmTurnRepoContract):
    """A conversation's model turns by their sequence (1010's index)."""

    def __init__(
        self, collection: DocumentCollectionAdapterContract[LlmTurnDocument]
    ) -> None:
        self._collection: DocumentCollectionAdapterContract[LlmTurnDocument] = (
            collection
        )

    def delete_by_conversation(self, conversation_id: ConversationId) -> DocumentCount:
        return self._collection.delete_by_range(
            DocumentFieldRange(
                field=SEQUENCE_NUMBER_FIELD, lower=DocumentFieldInteger(0)
            ),
            (field_equals(CONVERSATION_ID_FIELD, conversation_id),),
        )
