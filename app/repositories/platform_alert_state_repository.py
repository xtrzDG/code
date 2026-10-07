from collections.abc import Sequence

from app.contracts.document_store import DocumentCollectionAdapterContract
from app.contracts.monitoring import PlatformAlertStateRepoContract
from app.schemas.constants.monitoring import PlatformAlertCode
from app.schemas.domain.platform_alerts import PlatformAlertStateDocument


class PlatformAlertStateRepository(PlatformAlertStateRepoContract):
    """
    One row per platform alert, keyed by its code: every alert's state is
    one keyed read of a handful of rows (`get_many`), never a scan.
    """

    def __init__(
        self,
        collection: DocumentCollectionAdapterContract[PlatformAlertStateDocument],
    ) -> None:
        self._collection: DocumentCollectionAdapterContract[
            PlatformAlertStateDocument
        ] = collection

    def get_many(
        self, codes: Sequence[PlatformAlertCode]
    ) -> list[PlatformAlertStateDocument]:
        return self._collection.get_many([code.value for code in codes])

    def save(self, state: PlatformAlertStateDocument) -> None:
        self._collection.upsert(state.code.value, state)
