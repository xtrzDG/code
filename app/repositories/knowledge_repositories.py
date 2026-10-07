from collections.abc import Sequence

from app.contracts.repositories.knowledge_repositories import (
    KnowledgeItemRepoContract,
    ResourceRepoContract,
    ScheduleExceptionRepoContract,
)
from app.repositories.business_scoped_repository import BusinessScopedRepository
from app.repositories.document_queries import field_equals
from app.schemas.constants.knowledge import KnowledgeItemKind
from app.schemas.domain.knowledge import KnowledgeItemDocument
from app.schemas.domain.resources import ResourceDocument, ScheduleExceptionDocument
from app.schemas.dto.paging import KeysetSlice
from app.schemas.dto.storage_queries import DocumentFieldMatch, DocumentFilter
from app.schemas.typings.bookings.prefixed_id import ResourceId, ScheduleExceptionId
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.conversations.prefixed_id import MessageId
from app.schemas.typings.knowledge.booleans import IsKnowledgeItemActive
from app.schemas.typings.knowledge.prefixed_id import KnowledgeItemId
from app.schemas.typings.storage.constrained_integers import DocumentQueryLimit
from app.schemas.typings.storage.constrained_strings import DocumentFieldPath

KNOWLEDGE_KIND_FIELD: DocumentFieldPath = DocumentFieldPath("kind")
CORRECTION_OF_FIELD: DocumentFieldPath = DocumentFieldPath("correction_of")
KNOWLEDGE_UPDATED_AT_FIELD: DocumentFieldPath = DocumentFieldPath("updated_at")
KNOWLEDGE_IS_ACTIVE_FIELD: DocumentFieldPath = DocumentFieldPath("is_active")


class KnowledgeItemRepository(
    BusinessScopedRepository[KnowledgeItemDocument],
    KnowledgeItemRepoContract,
):
    def save(self, item: KnowledgeItemDocument) -> None:
        self._store(str(item.id), item)

    def get(
        self,
        business_id: BusinessId,
        item_id: KnowledgeItemId,
    ) -> KnowledgeItemDocument | None:
        return self._load(business_id, str(item_id))

    def list_by_business(
        self,
        business_id: BusinessId,
    ) -> list[KnowledgeItemDocument]:
        return self._list_in_business(business_id)

    def get_many(
        self,
        business_id: BusinessId,
        item_ids: Sequence[KnowledgeItemId],
    ) -> dict[KnowledgeItemId, KnowledgeItemDocument]:
        return {
            item.id: item
            for item in self._load_many(
                business_id, sorted({str(item_id) for item_id in item_ids})
            )
        }

    def page_by_business(
        self,
        business_id: BusinessId,
        window: KeysetSlice,
        kind: KnowledgeItemKind | None,
        is_active: IsKnowledgeItemActive | None,
    ) -> list[KnowledgeItemDocument]:
        matches: list[DocumentFieldMatch] = []
        if kind is not None:
            matches.append(field_equals(KNOWLEDGE_KIND_FIELD, kind))

        if is_active is not None:
            matches.append(field_equals(KNOWLEDGE_IS_ACTIVE_FIELD, is_active))

        return self._page_in_business(
            business_id,
            (KNOWLEDGE_UPDATED_AT_FIELD,),
            window,
            DocumentFilter(matches=tuple(matches)),
        )

    def list_by_kind(
        self,
        business_id: BusinessId,
        kind: KnowledgeItemKind,
        limit: DocumentQueryLimit,
    ) -> list[KnowledgeItemDocument]:
        return self._list_in_business(
            business_id, [field_equals(KNOWLEDGE_KIND_FIELD, kind)], limit=limit
        )

    def find_by_correction(
        self,
        business_id: BusinessId,
        message_id: MessageId,
    ) -> KnowledgeItemDocument | None:
        return self._find_in_business(
            business_id, [field_equals(CORRECTION_OF_FIELD, message_id)]
        )

    def delete(self, business_id: BusinessId, item_id: KnowledgeItemId) -> None:
        self._remove(business_id, str(item_id))


class ResourceRepository(
    BusinessScopedRepository[ResourceDocument],
    ResourceRepoContract,
):
    def save(self, resource: ResourceDocument) -> None:
        self._store(str(resource.id), resource)

    def get(
        self,
        business_id: BusinessId,
        resource_id: ResourceId,
    ) -> ResourceDocument | None:
        return self._load(business_id, str(resource_id))

    def list_by_business(self, business_id: BusinessId) -> list[ResourceDocument]:
        return self._list_in_business(business_id)


class ScheduleExceptionRepository(
    BusinessScopedRepository[ScheduleExceptionDocument],
    ScheduleExceptionRepoContract,
):
    def save(self, exception: ScheduleExceptionDocument) -> None:
        self._store(str(exception.id), exception)

    def list_by_business(
        self,
        business_id: BusinessId,
    ) -> list[ScheduleExceptionDocument]:
        return sorted(
            self._list_in_business(business_id), key=lambda exception: exception.date
        )

    def delete(
        self,
        business_id: BusinessId,
        exception_id: ScheduleExceptionId,
    ) -> None:
        self._remove(business_id, str(exception_id))
