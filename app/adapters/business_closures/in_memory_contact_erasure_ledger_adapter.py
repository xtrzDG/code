import threading

from app.contracts.contact_erasure_ledger import ContactErasureLedgerAdapterContract
from app.schemas.dto.business_closures.contact_erasure_ledger import (
    ContactErasureRecord,
)
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.contacts.prefixed_id import ContactId


class InMemoryContactErasureLedgerAdapter(ContactErasureLedgerAdapterContract):
    """
    The ledger of erased customers without a backup bucket (development,
    tests): there are no off-site backups to restore then; this copy lives
    as long as the process.
    """

    def __init__(self) -> None:
        self._records: dict[tuple[BusinessId, ContactId], ContactErasureRecord] = {}
        self._lock: threading.Lock = threading.Lock()

    def record(self, record: ContactErasureRecord) -> None:
        with self._lock:
            self._records.setdefault((record.business_id, record.contact_id), record)

    def read_all(self) -> list[ContactErasureRecord]:
        with self._lock:
            records: list[ContactErasureRecord] = list(self._records.values())

        return sorted(records, key=lambda record: int(record.erased_at))
