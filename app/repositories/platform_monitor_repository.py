from app.contracts.document_store import DocumentCollectionAdapterContract
from app.contracts.monitoring import PlatformMonitorRepoContract
from app.schemas.constants.monitoring import PlatformMonitor
from app.schemas.domain.platform_monitors import PlatformMonitorDocument


class PlatformMonitorRepository(PlatformMonitorRepoContract):
    """
    One row per watcher of the platform, keyed by its name: every read is
    one keyed read, never a scan (the table holds a row per watcher).
    """

    def __init__(
        self,
        collection: DocumentCollectionAdapterContract[PlatformMonitorDocument],
    ) -> None:
        self._collection: DocumentCollectionAdapterContract[PlatformMonitorDocument] = (
            collection
        )

    def get(self, monitor: PlatformMonitor) -> PlatformMonitorDocument | None:
        return self._collection.get(monitor.value)

    def save(self, mark: PlatformMonitorDocument) -> None:
        self._collection.upsert(mark.monitor.value, mark)
