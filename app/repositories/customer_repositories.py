"""The owner's saved segments and the team's customer settings (1140)."""

from collections.abc import Callable

from typed_time_provider import Microseconds

from app.contracts.repositories.customer_repositories import (
    CustomerSegmentRepoContract,
    CustomerSettingsRepoContract,
)
from app.repositories.business_scoped_repository import BusinessScopedRepository
from app.schemas.domain.customer_segments import CustomerSegmentDocument
from app.schemas.domain.customer_settings import CustomerSettingsDocument
from app.schemas.exceptions.application_errors import NotFoundError
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.contacts.prefixed_id import CustomerSegmentId
from app.utilities.customers.customer_keys import derive_customer_settings_id


class CustomerSegmentRepository(
    BusinessScopedRepository[CustomerSegmentDocument], CustomerSegmentRepoContract
):
    """A business's segments by business (a few each, at most MAX_SEGMENTS)."""

    def save(self, segment: CustomerSegmentDocument) -> None:
        self._store(str(segment.id), segment)

    def get(
        self, business_id: BusinessId, segment_id: CustomerSegmentId
    ) -> CustomerSegmentDocument | None:
        return self._load(business_id, str(segment_id))

    def list_by_business(
        self, business_id: BusinessId
    ) -> list[CustomerSegmentDocument]:
        return sorted(
            self._list_in_business(business_id),
            key=lambda segment: (int(segment.created_at), str(segment.id)),
        )

    def delete(self, business_id: BusinessId, segment_id: CustomerSegmentId) -> None:
        self._remove(business_id, str(segment_id))


class CustomerSettingsRepository(
    BusinessScopedRepository[CustomerSettingsDocument], CustomerSettingsRepoContract
):
    """One settings document per business, keyed by its derived id."""

    def get_by_business(
        self, business_id: BusinessId
    ) -> CustomerSettingsDocument | None:
        return self._load(business_id, str(derive_customer_settings_id(business_id)))

    def change(
        self,
        business_id: BusinessId,
        apply: Callable[[CustomerSettingsDocument], None],
        now: Microseconds,
    ) -> CustomerSettingsDocument:
        settings_id = derive_customer_settings_id(business_id)
        self._collection.insert_if_absent(
            str(settings_id),
            CustomerSettingsDocument(
                id=settings_id, business_id=business_id, created_at=now, updated_at=now
            ),
        )

        def change_settings(
            stored: CustomerSettingsDocument,
        ) -> CustomerSettingsDocument:
            apply(stored)
            stored.updated_at = now
            return stored

        changed: CustomerSettingsDocument | None = self._modify_in_business(
            business_id, str(settings_id), change_settings
        )
        if changed is None:
            raise NotFoundError(
                f"The customer settings of business {business_id} are gone."
            )

        return changed
