from collections.abc import Callable

from typed_time_provider import Microseconds

from app.contracts.repositories.customer_memory_repositories import (
    AssistantSettingsRepoContract,
)
from app.repositories.business_scoped_repository import BusinessScopedRepository
from app.schemas.domain.assistant_settings import AssistantSettingsDocument
from app.schemas.exceptions.application_errors import NotFoundError
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.utilities.memory.memory_keys import derive_assistant_settings_id


class AssistantSettingsRepository(
    BusinessScopedRepository[AssistantSettingsDocument],
    AssistantSettingsRepoContract,
):
    """One settings document per business, keyed by its derived id."""

    def get_by_business(
        self, business_id: BusinessId
    ) -> AssistantSettingsDocument | None:
        return self._load(business_id, str(derive_assistant_settings_id(business_id)))

    def change(
        self,
        business_id: BusinessId,
        apply: Callable[[AssistantSettingsDocument], None],
        now: Microseconds,
    ) -> AssistantSettingsDocument:
        settings_id = derive_assistant_settings_id(business_id)
        self._collection.insert_if_absent(
            str(settings_id),
            AssistantSettingsDocument(
                id=settings_id, business_id=business_id, created_at=now, updated_at=now
            ),
        )

        def change_settings(
            stored: AssistantSettingsDocument,
        ) -> AssistantSettingsDocument:
            apply(stored)
            stored.updated_at = now
            return stored

        changed: AssistantSettingsDocument | None = self._modify_in_business(
            business_id, str(settings_id), change_settings
        )
        if changed is None:
            raise NotFoundError(
                f"The assistant settings of business {business_id} are gone."
            )

        return changed
