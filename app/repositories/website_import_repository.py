from collections.abc import Callable

from typed_time_provider import Microseconds

from app.contracts.repositories.website_import_repositories import (
    WebsiteImportRepoContract,
)
from app.repositories.business_scoped_repository import BusinessScopedRepository
from app.schemas.constants.website_import import WebsiteImportStatus
from app.schemas.domain.website_imports import WebsiteImportDocument
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.website_import.prefixed_id import WebsiteImportId
from app.utilities.knowledge.website.website_import_keys import (
    derive_website_import_record_id,
)

ACTIVE_STATUSES: frozenset[WebsiteImportStatus] = frozenset(
    {WebsiteImportStatus.QUEUED, WebsiteImportStatus.READING}
)


class WebsiteImportRepository(
    BusinessScopedRepository[WebsiteImportDocument],
    WebsiteImportRepoContract,
):
    """The current website import of each business, keyed by its derived id."""

    def get_by_business(self, business_id: BusinessId) -> WebsiteImportDocument | None:
        return self._load(business_id, record_key(business_id))

    def start(
        self,
        website_import: WebsiteImportDocument,
        stale_before: Microseconds,
    ) -> WebsiteImportDocument | None:
        key: str = record_key(website_import.business_id)
        if self._collection.insert_if_absent(key, website_import):
            return None

        blocking: list[WebsiteImportDocument] = []

        def replace(stored: WebsiteImportDocument) -> WebsiteImportDocument | None:
            if stored.status in ACTIVE_STATUSES and stored.updated_at >= stale_before:
                blocking.append(stored)
                return None

            return website_import

        replaced: WebsiteImportDocument | None = self._modify_in_business(
            website_import.business_id, key, replace
        )
        if replaced is not None:
            return None

        # Blocked by a running import (or the record belongs elsewhere).
        return blocking[0] if blocking else self.get_by_business(
            website_import.business_id
        )

    def change(
        self,
        business_id: BusinessId,
        import_id: WebsiteImportId,
        apply: Callable[[WebsiteImportDocument], bool],
    ) -> WebsiteImportDocument | None:
        def change_current(
            stored: WebsiteImportDocument,
        ) -> WebsiteImportDocument | None:
            if stored.import_id != import_id or not apply(stored):
                return None

            return stored

        return self._modify_in_business(
            business_id, record_key(business_id), change_current
        )


def record_key(business_id: BusinessId) -> str:
    return str(derive_website_import_record_id(business_id))
