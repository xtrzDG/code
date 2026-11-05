from typed_time_provider import Microseconds

from app.contracts.meta_connection import (
    MetaConnectionStateChange,
    MetaConnectionStateRepoContract,
)
from app.repositories.business_scoped_repository import BusinessScopedRepository
from app.repositories.document_queries import time_range
from app.schemas.domain.meta_connections import MetaConnectionStateDocument
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.meta_connection.constrained_strings import (
    MetaConnectionStateHash,
)
from app.schemas.typings.storage.constrained_integers import DocumentCount
from app.schemas.typings.storage.constrained_strings import DocumentFieldPath

EXPIRES_AT_FIELD: DocumentFieldPath = DocumentFieldPath("expires_at")


class MetaConnectionStateRepository(
    BusinessScopedRepository[MetaConnectionStateDocument],
    MetaConnectionStateRepoContract,
):
    """
    Facebook sign-ins started on the Channels page (1212), keyed by the hash
    of their state and read only within their business; the daily purge
    deletes ended ones by `expires_at` across businesses (indexed).
    """

    def save(self, state: MetaConnectionStateDocument) -> None:
        self._store(str(state.state_hash), state)

    def get(
        self, business_id: BusinessId, state_hash: MetaConnectionStateHash
    ) -> MetaConnectionStateDocument | None:
        return self._load(business_id, str(state_hash))

    def modify(
        self,
        business_id: BusinessId,
        state_hash: MetaConnectionStateHash,
        change: MetaConnectionStateChange,
    ) -> MetaConnectionStateDocument | None:
        return self._modify_in_business(business_id, str(state_hash), change)

    def list_of_business(
        self, business_id: BusinessId
    ) -> list[MetaConnectionStateDocument]:
        return self._list_in_business(business_id)

    def delete(
        self, business_id: BusinessId, state_hash: MetaConnectionStateHash
    ) -> None:
        self._remove(business_id, str(state_hash))

    def delete_ended_before(self, moment: Microseconds) -> DocumentCount:
        return self._collection.delete_by_range(
            time_range(EXPIRES_AT_FIELD, ending_before=moment)
        )
