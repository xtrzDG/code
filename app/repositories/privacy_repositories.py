from collections.abc import Sequence

from typed_time_provider import Microseconds

from app.contracts.repositories.privacy_repositories import (
    BusinessExportChange,
    BusinessExportRepoContract,
    SuppressionEntryRepoContract,
)
from app.repositories.business_scoped_repository import BusinessScopedRepository
from app.repositories.document_queries import (
    CREATED_AT_FIELD,
    descending,
    time_range,
)
from app.schemas.domain.business_exports import BusinessExportDocument
from app.schemas.domain.suppression import SuppressionEntryDocument
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.privacy.prefixed_id import (
    BusinessExportId,
    SuppressionEntryId,
)
from app.schemas.typings.storage.booleans import IsDocumentInserted
from app.schemas.typings.storage.constrained_integers import DocumentQueryLimit
from app.schemas.typings.storage.constrained_strings import DocumentFieldPath

EXPIRES_AT_FIELD: DocumentFieldPath = DocumentFieldPath("expires_at")


class SuppressionEntryRepository(
    BusinessScopedRepository[SuppressionEntryDocument],
    SuppressionEntryRepoContract,
):
    """
    The suppression list, keyed by the id derived from the business and
    the identity's digest: inserted once, read by ids (no lookup field).
    """

    def insert_if_new(self, entry: SuppressionEntryDocument) -> IsDocumentInserted:
        return self._collection.insert_if_absent(str(entry.id), entry)

    def get_many(
        self,
        business_id: BusinessId,
        entry_ids: Sequence[SuppressionEntryId],
    ) -> list[SuppressionEntryDocument]:
        return self._load_many(business_id, [str(entry_id) for entry_id in entry_ids])

    def delete(self, business_id: BusinessId, entry_id: SuppressionEntryId) -> None:
        self._remove(business_id, str(entry_id))


class BusinessExportRepository(
    BusinessScopedRepository[BusinessExportDocument],
    BusinessExportRepoContract,
):
    """
    Full business exports: a business's newest first by `created_at`, and
    those whose link ran out by `expires_at` (indexed, migration 1113).
    """

    def save(self, export: BusinessExportDocument) -> None:
        self._store(str(export.id), export)

    def get(
        self, business_id: BusinessId, export_id: BusinessExportId
    ) -> BusinessExportDocument | None:
        return self._load(business_id, str(export_id))

    def update(
        self,
        business_id: BusinessId,
        export_id: BusinessExportId,
        change: BusinessExportChange,
    ) -> BusinessExportDocument | None:
        return self._modify_in_business(business_id, str(export_id), change)

    def list_latest(
        self, business_id: BusinessId, limit: DocumentQueryLimit
    ) -> list[BusinessExportDocument]:
        return self._list_in_business(
            business_id, order=descending(CREATED_AT_FIELD), limit=limit
        )

    def list_expiring_before(
        self, moment: Microseconds, limit: DocumentQueryLimit
    ) -> list[BusinessExportDocument]:
        return self._collection.list_by_range(
            time_range(EXPIRES_AT_FIELD, ending_before=moment), limit=limit
        )
