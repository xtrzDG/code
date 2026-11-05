from collections.abc import Callable

from app.contracts.document_store import DocumentCollectionAdapterContract
from app.contracts.repositories.brand_repositories import (
    BrandKnowledgeItemRepoContract,
    BrandRepoContract,
)
from app.repositories.document_queries import field_equals
from app.schemas.domain.brands import BrandDocument, BrandKnowledgeItemDocument
from app.schemas.exceptions.application_errors import NotFoundError
from app.schemas.typings.brands.prefixed_id import BrandId
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.knowledge.constrained_strings import KnowledgeShareKey
from app.schemas.typings.storage.constrained_strings import DocumentFieldPath
from app.schemas.typings.users.prefixed_id import UserId

MEMBER_USER_ID_FIELD: DocumentFieldPath = DocumentFieldPath("members[].user_id")
BRAND_ID_FIELD: DocumentFieldPath = DocumentFieldPath("brand_id")


class BrandRepository(BrandRepoContract):
    """Brands keyed by their id; every change is one step of the collection."""

    def __init__(self, collection: DocumentCollectionAdapterContract[BrandDocument]):
        self._collection: DocumentCollectionAdapterContract[BrandDocument] = collection

    def add(self, brand: BrandDocument) -> None:
        self._collection.upsert(str(brand.id), brand)

    def get(self, brand_id: BrandId) -> BrandDocument | None:
        return self._collection.get(str(brand_id))

    def list_by_member(self, user_id: UserId) -> list[BrandDocument]:
        return self._collection.list_by_fields(
            [field_equals(MEMBER_USER_ID_FIELD, user_id)]
        )

    def update(
        self,
        brand_id: BrandId,
        apply: Callable[[BrandDocument], None],
    ) -> BrandDocument:
        def change(stored: BrandDocument) -> BrandDocument:
            apply(stored)
            return stored

        updated: BrandDocument | None = self._collection.modify(str(brand_id), change)
        if updated is None:
            raise NotFoundError(f"Brand {brand_id} was not found.")

        return updated

    def claim_setup_fee(self, brand_id: BrandId, business_id: BusinessId) -> bool:
        holders: list[BusinessId] = []

        def claim(stored: BrandDocument) -> BrandDocument | None:
            if stored.setup_fee_business_id is not None:
                holders.append(stored.setup_fee_business_id)
                return None

            stored.setup_fee_business_id = business_id
            return stored

        claimed: BrandDocument | None = self._collection.modify(str(brand_id), claim)
        if claimed is not None:
            return True

        return holders == [business_id]

    def delete(self, brand_id: BrandId) -> None:
        self._collection.delete(str(brand_id))


class BrandKnowledgeItemRepository(BrandKnowledgeItemRepoContract):
    """
    A brand's shared items, stored under "<brand id>/<shared key>": one
    item per key and brand, guarded by the storage key itself.
    """

    def __init__(
        self,
        collection: DocumentCollectionAdapterContract[BrandKnowledgeItemDocument],
    ) -> None:
        self._collection: DocumentCollectionAdapterContract[
            BrandKnowledgeItemDocument
        ] = collection

    def add(self, item: BrandKnowledgeItemDocument) -> bool:
        return bool(
            self._collection.insert_if_absent(
                item_key(item.brand_id, item.shared_key), item
            )
        )

    def get(
        self,
        brand_id: BrandId,
        shared_key: KnowledgeShareKey,
    ) -> BrandKnowledgeItemDocument | None:
        return self._collection.get(item_key(brand_id, shared_key))

    def list_by_brand(self, brand_id: BrandId) -> list[BrandKnowledgeItemDocument]:
        return self._collection.list_by_fields([field_equals(BRAND_ID_FIELD, brand_id)])

    def modify(
        self,
        brand_id: BrandId,
        shared_key: KnowledgeShareKey,
        change: Callable[[BrandKnowledgeItemDocument], BrandKnowledgeItemDocument],
    ) -> BrandKnowledgeItemDocument | None:
        return self._collection.modify(item_key(brand_id, shared_key), change)

    def delete(self, brand_id: BrandId, shared_key: KnowledgeShareKey) -> None:
        self._collection.delete(item_key(brand_id, shared_key))


def item_key(brand_id: BrandId, shared_key: KnowledgeShareKey) -> str:
    """The storage key of a brand's shared item."""

    return f"{brand_id}/{shared_key}"
