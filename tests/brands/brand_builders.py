"""Brands, locations and shared facts for the brand tests."""

from typed_time_provider import Microseconds

from app.adapters.storage.in_memory_document_collection import (
    InMemoryDocumentCollectionAdapter,
)
from app.repositories.business_repositories import BusinessRepository
from app.schemas.constants.brands import BrandMemberRole
from app.schemas.constants.knowledge import KnowledgeItemKind
from app.schemas.domain.brands import (
    BrandDocument,
    BrandKnowledgeItemDocument,
    BrandMember,
)
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.typings.billing.constrained_integers import MoneyAmountMinor
from app.schemas.typings.brands.strings import BrandName
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.knowledge.constrained_strings import KnowledgeShareKey
from app.schemas.typings.knowledge.strings import KnowledgeBody, KnowledgeTitle
from app.schemas.typings.localization.constrained_strings import CurrencyCode
from app.schemas.typings.users.prefixed_id import UserId
from tests.foundation.builders import build_business


def build_brand(
    owner_id: UserId,
    managers: dict[UserId, list[BusinessId]] | None = None,
) -> BrandDocument:
    return BrandDocument(
        name=BrandName("Mtsvane Ezo"),
        members=[
            BrandMember(user_id=owner_id, role=BrandMemberRole.BRAND_OWNER),
            *(
                BrandMember(
                    user_id=user_id,
                    role=BrandMemberRole.REGIONAL_MANAGER,
                    business_ids=business_ids,
                )
                for user_id, business_ids in (managers or {}).items()
            ),
        ],
    )


def build_location(
    brand: BrandDocument | None,
    owner_id: UserId,
    created_at: int = 1,
) -> BusinessDocument:
    location = build_business(owner_id)
    return location.model_copy(
        update={
            "brand_id": None if brand is None else brand.id,
            "created_at": Microseconds(created_at),
            "updated_at": Microseconds(created_at),
        }
    )


def build_shared_fact(
    brand: BrandDocument,
    key: str,
    title: str,
    price_minor: int | None = None,
    currency_code: str | None = None,
    is_active: bool = True,
) -> BrandKnowledgeItemDocument:
    return BrandKnowledgeItemDocument(
        brand_id=brand.id,
        shared_key=KnowledgeShareKey(key),
        kind=KnowledgeItemKind.FAQ,
        title=KnowledgeTitle(title),
        body=KnowledgeBody(f"{title}: the brand's answer."),
        price_minor=None if price_minor is None else MoneyAmountMinor(price_minor),
        currency_code=None if currency_code is None else CurrencyCode(currency_code),
        is_active=is_active,
    )


def in_memory_business_repo() -> BusinessRepository:
    return BusinessRepository(
        InMemoryDocumentCollectionAdapter[BusinessDocument](BusinessDocument)
    )
