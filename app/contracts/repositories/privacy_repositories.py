"""
Persistence contracts of the suppression list and the full business
exports (migration 1113).
"""

from collections.abc import Callable, Sequence
from typing import Protocol

from typed_time_provider import Microseconds

from app.contracts.repo_contract import RepoContract
from app.schemas.domain.business_exports import BusinessExportDocument
from app.schemas.domain.suppression import SuppressionEntryDocument
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.privacy.prefixed_id import (
    BusinessExportId,
    SuppressionEntryId,
)
from app.schemas.typings.storage.booleans import IsDocumentInserted
from app.schemas.typings.storage.constrained_integers import DocumentQueryLimit

type BusinessExportChange = Callable[
    [BusinessExportDocument], BusinessExportDocument | None
]


class SuppressionEntryRepoContract(RepoContract, Protocol):
    def insert_if_new(self, entry: SuppressionEntryDocument) -> IsDocumentInserted:
        """False, and nothing written, when the identity is listed already."""
        raise NotImplementedError

    def get_many(
        self,
        business_id: BusinessId,
        entry_ids: Sequence[SuppressionEntryId],
    ) -> list[SuppressionEntryDocument]:
        """The business's entries of these ids (missing ones skipped), one read."""
        raise NotImplementedError

    def delete(self, business_id: BusinessId, entry_id: SuppressionEntryId) -> None:
        raise NotImplementedError


class BusinessExportRepoContract(RepoContract, Protocol):
    def save(self, export: BusinessExportDocument) -> None:
        raise NotImplementedError

    def get(
        self, business_id: BusinessId, export_id: BusinessExportId
    ) -> BusinessExportDocument | None:
        raise NotImplementedError

    def update(
        self,
        business_id: BusinessId,
        export_id: BusinessExportId,
        change: BusinessExportChange,
    ) -> BusinessExportDocument | None:
        """
        Store what `change` makes of the export as stored now, in one step;
        None, and nothing written, when it is missing or `change` says None.
        """
        raise NotImplementedError

    def list_latest(
        self, business_id: BusinessId, limit: DocumentQueryLimit
    ) -> list[BusinessExportDocument]:
        """The business's exports, the newest first."""
        raise NotImplementedError

    def list_expiring_before(
        self, moment: Microseconds, limit: DocumentQueryLimit
    ) -> list[BusinessExportDocument]:
        """Exports of every business whose link ran out before `moment`."""
        raise NotImplementedError
