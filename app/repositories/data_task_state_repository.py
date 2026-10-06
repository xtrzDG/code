from collections.abc import Sequence

from app.contracts.data_tasks import DataTaskStateRepoContract
from app.contracts.document_store import DocumentCollectionAdapterContract
from app.schemas.domain.data_tasks import DataTaskStateDocument
from app.schemas.typings.maintenance.constrained_strings import DataTaskKey


class DataTaskStateRepository(DataTaskStateRepoContract):
    """
    The data tasks' progress, one row per task keyed by the task's key:
    every read is one keyed read of the registry's few dozen keys, never a
    scan.
    """

    def __init__(
        self,
        collection: DocumentCollectionAdapterContract[DataTaskStateDocument],
    ) -> None:
        self._collection: DocumentCollectionAdapterContract[DataTaskStateDocument] = (
            collection
        )

    def get_many(self, keys: Sequence[DataTaskKey]) -> list[DataTaskStateDocument]:
        return self._collection.get_many([str(key) for key in keys])

    def save(self, state: DataTaskStateDocument) -> None:
        self._collection.upsert(str(state.key), state)
