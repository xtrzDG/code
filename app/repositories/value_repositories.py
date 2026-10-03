from app.contracts.repositories.value_repositories import (
    DigestPreferencesRepoContract,
    ValueReportRepoContract,
    ValueSettingsRepoContract,
)
from app.repositories.business_scoped_repository import BusinessScopedRepository
from app.repositories.document_queries import field_equals
from app.schemas.constants.value import ValueReportKind
from app.schemas.domain.value_reports import ValueReportDocument
from app.schemas.domain.value_settings import (
    DigestPreferencesDocument,
    ValueSettingsDocument,
)
from app.schemas.dto.paging import KeysetSlice
from app.schemas.dto.storage_queries import DocumentFilter
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.storage.booleans import IsDocumentInserted
from app.schemas.typings.storage.constrained_strings import DocumentFieldPath
from app.schemas.typings.users.prefixed_id import UserId
from app.schemas.typings.value.prefixed_id import ValueReportId
from app.utilities.value.value_keys import (
    digest_preferences_id_of,
    value_settings_id_of,
)

KIND_FIELD: DocumentFieldPath = DocumentFieldPath("kind")
STARTS_AT_FIELD: DocumentFieldPath = DocumentFieldPath("starts_at")


class ValueSettingsRepository(
    BusinessScopedRepository[ValueSettingsDocument],
    ValueSettingsRepoContract,
):
    """One value settings document per business, keyed by the derived id."""

    def get_by_business(self, business_id: BusinessId) -> ValueSettingsDocument | None:
        return self._load(business_id, str(value_settings_id_of(business_id)))

    def save(self, settings: ValueSettingsDocument) -> None:
        self._store(str(settings.id), settings)


class DigestPreferencesRepository(
    BusinessScopedRepository[DigestPreferencesDocument],
    DigestPreferencesRepoContract,
):
    """One owner's digest choices per business, keyed by the derived id."""

    def get(
        self,
        business_id: BusinessId,
        user_id: UserId,
    ) -> DigestPreferencesDocument | None:
        return self._load(
            business_id, str(digest_preferences_id_of(business_id, user_id))
        )

    def save(self, preferences: DigestPreferencesDocument) -> None:
        self._store(str(preferences.id), preferences)


class ValueReportRepository(
    BusinessScopedRepository[ValueReportDocument],
    ValueReportRepoContract,
):
    """
    Stored digests and monthly reports, keyed by the id derived from the
    business, kind and period; pages by kind newest period first
    (`(business_id, doc_kind, doc_starts_at)`, migration 1061).
    """

    def get(
        self,
        business_id: BusinessId,
        report_id: ValueReportId,
    ) -> ValueReportDocument | None:
        return self._load(business_id, str(report_id))

    def insert_if_new(self, report: ValueReportDocument) -> IsDocumentInserted:
        return self._collection.insert_if_absent(str(report.id), report)

    def page_by_business(
        self,
        business_id: BusinessId,
        kind: ValueReportKind,
        window: KeysetSlice,
    ) -> list[ValueReportDocument]:
        return self._page_in_business(
            business_id,
            (STARTS_AT_FIELD,),
            window,
            DocumentFilter(matches=(field_equals(KIND_FIELD, kind),)),
        )
