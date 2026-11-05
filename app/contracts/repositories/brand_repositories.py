"""
Persistence contracts of brands (chains of locations) and the knowledge
their locations share. Both are platform-wide: a brand spans businesses.
Implementations return independent copies.
"""

from collections.abc import Callable
from typing import Protocol

from app.contracts.repo_contract import RepoContract
from app.schemas.domain.brands import BrandDocument, BrandKnowledgeItemDocument
from app.schemas.typings.brands.prefixed_id import BrandId
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.knowledge.constrained_strings import KnowledgeShareKey
from app.schemas.typings.users.prefixed_id import UserId


class BrandRepoContract(RepoContract, Protocol):
    def add(self, brand: BrandDocument) -> None:
        """Store a new brand."""
        raise NotImplementedError

    def get(self, brand_id: BrandId) -> BrandDocument | None:
        raise NotImplementedError

    def list_by_member(self, user_id: UserId) -> list[BrandDocument]:
        """The brands the person is a member of (an indexed lookup)."""
        raise NotImplementedError

    def update(
        self,
        brand_id: BrandId,
        apply: Callable[[BrandDocument], None],
    ) -> BrandDocument:
        """
        Apply a change to the brand as stored now and store it in one step
        (no other write in between); `apply` may raise to refuse, and
        nothing is stored then. NotFoundError for a missing brand.
        """
        raise NotImplementedError

    def claim_setup_fee(self, brand_id: BrandId, business_id: BusinessId) -> bool:
        """
        Make `business_id` the location that carries the brand's one setup
        fee, in one step, unless another location already does. True when
        the business carries it (now or before), False when another does
        (or the brand is gone).
        """
        raise NotImplementedError

    def delete(self, brand_id: BrandId) -> None:
        raise NotImplementedError


class BrandKnowledgeItemRepoContract(RepoContract, Protocol):
    def add(self, item: BrandKnowledgeItemDocument) -> bool:
        """
        Store a new shared item in one atomic step: False, and nothing
        stored, when the brand already has an item with its shared key.
        """
        raise NotImplementedError

    def get(
        self,
        brand_id: BrandId,
        shared_key: KnowledgeShareKey,
    ) -> BrandKnowledgeItemDocument | None:
        raise NotImplementedError

    def list_by_brand(self, brand_id: BrandId) -> list[BrandKnowledgeItemDocument]:
        """A brand's shared items, oldest first (an indexed lookup)."""
        raise NotImplementedError

    def modify(
        self,
        brand_id: BrandId,
        shared_key: KnowledgeShareKey,
        change: Callable[[BrandKnowledgeItemDocument], BrandKnowledgeItemDocument],
    ) -> BrandKnowledgeItemDocument | None:
        """Store what `change` makes of the item as stored now; None if gone."""
        raise NotImplementedError

    def delete(self, brand_id: BrandId, shared_key: KnowledgeShareKey) -> None:
        raise NotImplementedError
