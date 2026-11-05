"""
The ledger of erased customers kept outside the database (the backup
bucket): a restored backup older than an erasure holds the customer's data
again, and this copy names every erasure since, so it is applied again.
"""

from typing import Protocol

from app.contracts.adapter_contract import AdapterContract
from app.schemas.dto.business_closures.contact_erasure_ledger import (
    ContactErasureRecord,
)


class ContactErasureLedgerAdapterContract(AdapterContract, Protocol):
    """
    One record per erased customer, never deleted (no personal data, ids
    only), read by the daily `reapply_contact_erasures` and counted by the
    restore drill.
    """

    def record(self, record: ContactErasureRecord) -> None:
        """
        Keep the record (writing it again changes nothing). Raises
        ExternalServiceError when the copy cannot be written (the queued
        job retries).
        """
        raise NotImplementedError

    def read_all(self) -> list[ContactErasureRecord]:
        """
        Every record kept, oldest erasure first. Raises ExternalServiceError
        on an object that is no record.
        """
        raise NotImplementedError
