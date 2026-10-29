from collections.abc import Sequence

from app.contracts.document_store import DocumentCollectionAdapterContract
from app.contracts.platform_status import PlatformStatusDayRepoContract
from app.schemas.domain.platform_status import PlatformStatusDayDocument
from app.schemas.typings.platform_status.constrained_strings import StatusDay


class PlatformStatusDayRepository(PlatformStatusDayRepoContract):
    """
    The status page's history, one row per UTC day keyed by the day
    (a platform collection, migration 1111): ninety keyed reads at most.
    """

    def __init__(
        self,
        collection: DocumentCollectionAdapterContract[PlatformStatusDayDocument],
    ) -> None:
        self._collection: DocumentCollectionAdapterContract[
            PlatformStatusDayDocument
        ] = collection

    def get_many(self, days: Sequence[StatusDay]) -> list[PlatformStatusDayDocument]:
        return self._collection.get_many([str(day) for day in days])

    def save(self, day: PlatformStatusDayDocument) -> None:
        self._collection.upsert(str(day.day), day)
