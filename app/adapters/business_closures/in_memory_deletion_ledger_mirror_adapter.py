import threading

from app.contracts.business_erasure import DeletionLedgerMirrorAdapterContract
from app.schemas.dto.business_closures.deletion_ledger import DeletionLedgerRecord
from app.schemas.typings.businesses.prefixed_id import BusinessId


class InMemoryDeletionLedgerMirrorAdapter(DeletionLedgerMirrorAdapterContract):
    """
    The ledger's copy without a backup bucket (development, tests): there
    are no off-site backups to restore then, so the database's own ledger
    is the whole story; this copy lives as long as the process.
    """

    def __init__(self) -> None:
        self._records: dict[BusinessId, DeletionLedgerRecord] = {}
        self._lock: threading.Lock = threading.Lock()

    def record(self, record: DeletionLedgerRecord) -> None:
        with self._lock:
            self._records.setdefault(record.business_id, record)

    def read_all(self) -> list[DeletionLedgerRecord]:
        with self._lock:
            records: list[DeletionLedgerRecord] = list(self._records.values())

        return sorted(records, key=lambda record: int(record.started_at))
