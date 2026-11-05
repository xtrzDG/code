from typed_time_provider import Microseconds

from app.contracts.document_store import DocumentCollectionAdapterContract
from app.contracts.health import WorkerHeartbeatRepoContract
from app.repositories.document_queries import time_range
from app.schemas.domain.jobs import WorkerHeartbeatDocument
from app.schemas.typings.storage.constrained_integers import (
    DocumentCount,
    DocumentQueryLimit,
)
from app.schemas.typings.storage.constrained_strings import DocumentFieldPath

BEAT_AT_FIELD: DocumentFieldPath = DocumentFieldPath("beat_at")
# Every pulse is written after the epoch: the open range that finds them.
EPOCH: Microseconds = Microseconds(0)


class WorkerHeartbeatRepository(WorkerHeartbeatRepoContract):
    """
    One row per worker process, keyed by its id. The freshest pulse and the
    purge are indexed range queries on `beat_at`.
    """

    def __init__(
        self,
        collection: DocumentCollectionAdapterContract[WorkerHeartbeatDocument],
    ) -> None:
        self._collection: DocumentCollectionAdapterContract[WorkerHeartbeatDocument] = (
            collection
        )

    def save(self, heartbeat: WorkerHeartbeatDocument) -> None:
        self._collection.upsert(str(heartbeat.id), heartbeat)

    def find_freshest(self) -> WorkerHeartbeatDocument | None:
        freshest: list[WorkerHeartbeatDocument] = self._collection.list_by_range(
            time_range(BEAT_AT_FIELD, starting_at=EPOCH),
            is_descending=True,
            limit=DocumentQueryLimit(1),
        )
        return freshest[0] if freshest else None

    def delete_beaten_before(self, beaten_before: Microseconds) -> DocumentCount:
        return self._collection.delete_by_range(
            time_range(BEAT_AT_FIELD, ending_before=beaten_before)
        )
