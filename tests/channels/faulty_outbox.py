"""An outbox repository that fails on purpose (fault injection)."""

from app.contracts.document_store import DocumentCollectionAdapterContract
from app.repositories.delivery_repositories import OutboundMessageRepository
from app.schemas.domain.outbound_messages import OutboundMessageDocument
from app.schemas.typings.storage.booleans import IsDocumentInserted


class FaultyOutboundMessageRepository(OutboundMessageRepository):
    """Raises the queued errors, one per insert, before storing anything."""

    def __init__(
        self,
        collection: DocumentCollectionAdapterContract[OutboundMessageDocument],
    ) -> None:
        super().__init__(collection)
        self.insert_failures: list[Exception] = []

    def insert_if_new(self, message: OutboundMessageDocument) -> IsDocumentInserted:
        if self.insert_failures:
            raise self.insert_failures.pop(0)

        return super().insert_if_new(message)
