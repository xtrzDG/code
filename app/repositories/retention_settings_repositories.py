from app.contracts.repositories.retention_repositories import (
    BusinessPrivacySettingsRepoContract,
    RetentionPurgeStateRepoContract,
)
from app.repositories.business_scoped_repository import BusinessScopedRepository
from app.schemas.domain.business_privacy_settings import (
    BusinessPrivacySettingsDocument,
)
from app.schemas.domain.retention_purges import RetentionPurgeStateDocument
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.utilities.privacy.retention_keys import (
    privacy_settings_id_of,
    retention_purge_state_id_of,
)


class BusinessPrivacySettingsRepository(
    BusinessScopedRepository[BusinessPrivacySettingsDocument],
    BusinessPrivacySettingsRepoContract,
):
    """One privacy settings document per business, keyed by the derived id."""

    def get_or_default(
        self, business_id: BusinessId
    ) -> BusinessPrivacySettingsDocument:
        settings_id = privacy_settings_id_of(business_id)
        stored: BusinessPrivacySettingsDocument | None = self._load(
            business_id, str(settings_id)
        )
        if stored is not None:
            return stored

        return BusinessPrivacySettingsDocument(id=settings_id, business_id=business_id)

    def save(self, settings: BusinessPrivacySettingsDocument) -> None:
        self._store(str(settings.id), settings)


class RetentionPurgeStateRepository(
    BusinessScopedRepository[RetentionPurgeStateDocument],
    RetentionPurgeStateRepoContract,
):
    """One purge state per business, keyed by the derived id."""

    def get_or_new(self, business_id: BusinessId) -> RetentionPurgeStateDocument:
        state_id = retention_purge_state_id_of(business_id)
        stored: RetentionPurgeStateDocument | None = self._load(
            business_id, str(state_id)
        )
        if stored is not None:
            return stored

        return RetentionPurgeStateDocument(id=state_id, business_id=business_id)

    def save(self, state: RetentionPurgeStateDocument) -> None:
        self._store(str(state.id), state)
