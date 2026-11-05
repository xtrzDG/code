"""
The steps of a subscription's life (migration 1161): a business's steps
through the business index, one kind's steps across businesses through
the (kind, occurred_at) index.
"""

from typed_time_provider import Microseconds

from app.contracts.repositories.subscription_event_repositories import (
    SubscriptionEventRepoContract,
)
from app.repositories.business_scoped_repository import BusinessScopedRepository
from app.repositories.document_queries import field_equals, time_range
from app.schemas.constants.subscription_lifecycle import SubscriptionEventKind
from app.schemas.domain.subscription_events import SubscriptionEventDocument
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.storage.constrained_strings import DocumentFieldPath
from app.schemas.typings.subscription_lifecycle.prefixed_id import (
    SubscriptionEventId,
)

KIND_FIELD: DocumentFieldPath = DocumentFieldPath("kind")
OCCURRED_AT_FIELD: DocumentFieldPath = DocumentFieldPath("occurred_at")


class SubscriptionEventRepository(
    BusinessScopedRepository[SubscriptionEventDocument],
    SubscriptionEventRepoContract,
):
    """Steps keyed by id; a win-back step's id derives from its stage."""

    def record(self, event: SubscriptionEventDocument) -> bool:
        return bool(self._collection.insert_if_absent(str(event.id), event))

    def get(
        self, business_id: BusinessId, event_id: SubscriptionEventId
    ) -> SubscriptionEventDocument | None:
        return self._load(business_id, str(event_id))

    def list_by_business(
        self, business_id: BusinessId
    ) -> list[SubscriptionEventDocument]:
        return sorted(
            self._list_in_business(business_id),
            key=lambda event: (int(event.occurred_at), int(event.created_at)),
        )

    def list_of_kind(
        self,
        kind: SubscriptionEventKind,
        occurred_from: Microseconds,
        occurred_before: Microseconds,
    ) -> list[SubscriptionEventDocument]:
        return self._collection.list_by_range(
            time_range(
                OCCURRED_AT_FIELD,
                starting_at=occurred_from,
                ending_before=occurred_before,
            ),
            (field_equals(KIND_FIELD, kind),),
        )
