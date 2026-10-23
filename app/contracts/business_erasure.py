"""
Every stored row of one business, across every table (the hard delete), and
the deletion ledger's copy outside the database.
"""

from collections.abc import Sequence
from typing import Protocol

from app.contracts.adapter_contract import AdapterContract
from app.schemas.dto.business_closures.business_rows import BusinessTableRows
from app.schemas.dto.business_closures.deletion_ledger import DeletionLedgerRecord
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.storage.constrained_strings import DocumentCollectionName


class BusinessRowEraserAdapterContract(AdapterContract, Protocol):
    """
    The business's rows in every table that names a business, read and
    deleted platform-wide (on Postgres through the platform pool, whose
    role sees every business; row-level security keeps the tenant pool
    from ever doing this). The tables the law keeps (the audit log and its
    chains, issued invoices and their commissions:
    `app/utilities/business_closures/retained_tables.py`) are counted but
    never deleted from.
    """

    def count_rows(self, business_id: BusinessId) -> list[BusinessTableRows]:
        """The tables holding rows of the business (retained ones too), by name."""
        raise NotImplementedError

    def erase_rows(
        self,
        business_id: BusinessId,
        tables: Sequence[DocumentCollectionName] | None = None,
    ) -> list[BusinessTableRows]:
        """
        Delete the business's rows of these tables (None: of every table but
        the retained ones), in small batches so no long lock is held, the
        business's own row last; what each table lost. Deleting what is gone
        already is not an error, so a retried deletion continues.
        """
        raise NotImplementedError


class DeletionLedgerMirrorAdapterContract(AdapterContract, Protocol):
    """
    The deletion ledger kept outside the database: a restored backup holds
    the ledger as it was then, so the restore drill also applies what this
    copy holds, and a business deleted after the backup stays deleted.
    """

    def record(self, record: DeletionLedgerRecord) -> None:
        """
        Keep the record (writing it again changes nothing). Raises
        ExternalServiceError when the copy cannot be written (the deletion
        job retries).
        """
        raise NotImplementedError

    def read_all(self) -> list[DeletionLedgerRecord]:
        """Every record kept, oldest first."""
        raise NotImplementedError
