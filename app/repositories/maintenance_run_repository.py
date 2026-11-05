from typed_time_provider import Microseconds

from app.contracts.document_store import DocumentCollectionAdapterContract
from app.contracts.monitoring import MaintenanceRunRepoContract
from app.repositories.document_queries import field_equals, time_range
from app.schemas.constants.monitoring import MaintenanceRunKind
from app.schemas.domain.maintenance_runs import MaintenanceRunDocument
from app.schemas.typings.storage.constrained_integers import DocumentQueryLimit
from app.schemas.typings.storage.constrained_strings import DocumentFieldPath

KIND_FIELD: DocumentFieldPath = DocumentFieldPath("kind")
FINISHED_AT_FIELD: DocumentFieldPath = DocumentFieldPath("finished_at")
EPOCH: Microseconds = Microseconds(0)


class MaintenanceRunRepository(MaintenanceRunRepoContract):
    """
    The recorded backups and restore drills; the last of a kind is one
    probe of the (doc_kind, doc_finished_at) index (1093).
    """

    def __init__(
        self,
        collection: DocumentCollectionAdapterContract[MaintenanceRunDocument],
    ) -> None:
        self._collection: DocumentCollectionAdapterContract[MaintenanceRunDocument] = (
            collection
        )

    def record(self, run: MaintenanceRunDocument) -> None:
        self._collection.upsert(str(run.id), run)

    def find_latest(self, kind: MaintenanceRunKind) -> MaintenanceRunDocument | None:
        latest: list[MaintenanceRunDocument] = self._collection.list_by_range(
            time_range(FINISHED_AT_FIELD, starting_at=EPOCH),
            matches=[field_equals(KIND_FIELD, kind)],
            is_descending=True,
            limit=DocumentQueryLimit(1),
        )
        return latest[0] if latest else None
