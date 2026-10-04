from collections.abc import Sequence

from typed_time_provider import Microseconds

from app.contracts.document_store import DocumentCollectionAdapterContract
from app.contracts.repositories.delivery_repositories import (
    InboundEventChange,
    InboundEventRepoContract,
    OutboundMessageChange,
    OutboundMessageRepoContract,
)
from app.repositories.business_scoped_repository import BusinessScopedRepository
from app.repositories.document_queries import ascending, field_equals, time_range
from app.schemas.constants.deliveries import OutboundMessageStatus
from app.schemas.domain.inbound_events import InboundEventDocument
from app.schemas.domain.outbound_messages import OutboundMessageDocument
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.deliveries.constrained_strings import OutboundRecipientKey
from app.schemas.typings.deliveries.prefixed_id import InboundEventId, OutboundMessageId
from app.schemas.typings.storage.booleans import IsDocumentInserted
from app.schemas.typings.storage.constrained_integers import DocumentCount
from app.schemas.typings.storage.constrained_strings import DocumentFieldPath

CREATED_AT_FIELD: DocumentFieldPath = DocumentFieldPath("created_at")
RECIPIENT_KEY_FIELD: DocumentFieldPath = DocumentFieldPath("recipient_key")
STATUS_FIELD: DocumentFieldPath = DocumentFieldPath("status")


class InboundEventRepository(InboundEventRepoContract):
    """
    The inbox, keyed by the derived event id (the primary key; on Postgres
    also a unique index of business, channel and provider message id).
    A platform collection: platform events have no business, so every read
    checks the business itself.
    """

    def __init__(
        self,
        collection: DocumentCollectionAdapterContract[InboundEventDocument],
    ) -> None:
        self._collection: DocumentCollectionAdapterContract[InboundEventDocument] = (
            collection
        )

    def insert_if_new(self, event: InboundEventDocument) -> IsDocumentInserted:
        return self._collection.insert_if_absent(str(event.id), event)

    def get(
        self,
        business_id: BusinessId | None,
        event_id: InboundEventId,
    ) -> InboundEventDocument | None:
        event: InboundEventDocument | None = self._collection.get(str(event_id))
        if event is None or event.business_id != business_id:
            return None

        return event

    def update(
        self,
        business_id: BusinessId | None,
        event_id: InboundEventId,
        change: InboundEventChange,
    ) -> InboundEventDocument | None:
        def change_own(stored: InboundEventDocument) -> InboundEventDocument | None:
            if stored.business_id != business_id:
                return None

            return change(stored)

        return self._collection.modify(str(event_id), change_own)

    def delete_created_before(self, created_before: Microseconds) -> DocumentCount:
        return self._collection.delete_by_range(
            time_range(CREATED_AT_FIELD, ending_before=created_before)
        )


class OutboundMessageRepository(
    BusinessScopedRepository[OutboundMessageDocument],
    OutboundMessageRepoContract,
):
    """
    The outbox of one business per row, keyed by the id derived from the
    idempotency key (on Postgres also unique per business and key).
    """

    def insert_if_new(self, message: OutboundMessageDocument) -> IsDocumentInserted:
        return self._collection.insert_if_absent(str(message.id), message)

    def get(
        self,
        business_id: BusinessId,
        message_id: OutboundMessageId,
    ) -> OutboundMessageDocument | None:
        return self._load(business_id, str(message_id))

    def get_many(
        self,
        business_id: BusinessId,
        message_ids: Sequence[OutboundMessageId],
    ) -> list[OutboundMessageDocument]:
        return self._load_many(
            business_id, [str(message_id) for message_id in message_ids]
        )

    def update(
        self,
        business_id: BusinessId,
        message_id: OutboundMessageId,
        change: OutboundMessageChange,
    ) -> OutboundMessageDocument | None:
        return self._modify_in_business(business_id, str(message_id), change)

    def list_pending_for_recipient(
        self,
        business_id: BusinessId,
        recipient_key: OutboundRecipientKey,
    ) -> list[OutboundMessageDocument]:
        return self._list_in_business(
            business_id,
            (
                field_equals(RECIPIENT_KEY_FIELD, recipient_key),
                field_equals(STATUS_FIELD, OutboundMessageStatus.PENDING),
            ),
            order=ascending(CREATED_AT_FIELD),
        )

    def delete_created_before(self, created_before: Microseconds) -> DocumentCount:
        return self._collection.delete_by_range(
            time_range(CREATED_AT_FIELD, ending_before=created_before)
        )
