"""
Persistence contracts of knowledge items, resources and schedule exceptions.

Implementations return independent copies: mutating a returned document does
not change stored state until it is saved. Every business-owned document is
looked up through its business id, so one tenant never sees another's data.
"""

from collections.abc import Sequence
from typing import Protocol

from app.contracts.repo_contract import RepoContract
from app.schemas.constants.knowledge import KnowledgeItemKind
from app.schemas.domain.knowledge import KnowledgeItemDocument
from app.schemas.domain.resources import ResourceDocument, ScheduleExceptionDocument
from app.schemas.typings.bookings.prefixed_id import ResourceId, ScheduleExceptionId
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.knowledge.prefixed_id import KnowledgeItemId
from app.schemas.typings.storage.constrained_integers import DocumentQueryLimit


class KnowledgeItemRepoContract(RepoContract, Protocol):
    def save(self, item: KnowledgeItemDocument) -> None:
        raise NotImplementedError

    def get(
        self,
        business_id: BusinessId,
        item_id: KnowledgeItemId,
    ) -> KnowledgeItemDocument | None:
        raise NotImplementedError

    def list_by_business(
        self,
        business_id: BusinessId,
    ) -> list[KnowledgeItemDocument]:
        raise NotImplementedError

    def get_many(
        self,
        business_id: BusinessId,
        item_ids: Sequence[KnowledgeItemId],
    ) -> dict[KnowledgeItemId, KnowledgeItemDocument]:
        """The business's items of these ids (missing ones left out), one read."""
        raise NotImplementedError

    def list_by_kind(
        self,
        business_id: BusinessId,
        kind: KnowledgeItemKind,
        limit: DocumentQueryLimit,
    ) -> list[KnowledgeItemDocument]:
        """The business's first-written items of a kind (an indexed query)."""
        raise NotImplementedError

    def delete(self, business_id: BusinessId, item_id: KnowledgeItemId) -> None:
        raise NotImplementedError


class ResourceRepoContract(RepoContract, Protocol):
    def save(self, resource: ResourceDocument) -> None:
        raise NotImplementedError

    def get(
        self,
        business_id: BusinessId,
        resource_id: ResourceId,
    ) -> ResourceDocument | None:
        raise NotImplementedError

    def list_by_business(self, business_id: BusinessId) -> list[ResourceDocument]:
        raise NotImplementedError


class ScheduleExceptionRepoContract(RepoContract, Protocol):
    def save(self, exception: ScheduleExceptionDocument) -> None:
        raise NotImplementedError

    def list_by_business(
        self,
        business_id: BusinessId,
    ) -> list[ScheduleExceptionDocument]:
        raise NotImplementedError

    def delete(
        self,
        business_id: BusinessId,
        exception_id: ScheduleExceptionId,
    ) -> None:
        raise NotImplementedError
