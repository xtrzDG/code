from base_pydantic_schemas import BaseDocument, PersistentDocument, SchemaVersion
from pydantic import Field

from app.schemas.constants.brands import BrandMemberRole
from app.schemas.constants.knowledge import KnowledgeItemKind
from app.schemas.typings.billing.constrained_integers import MoneyAmountMinor
from app.schemas.typings.brands.prefixed_id import BrandId
from app.schemas.typings.brands.strings import BrandName
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.knowledge.booleans import IsKnowledgeItemActive
from app.schemas.typings.knowledge.constrained_strings import (
    KnowledgeShareKey,
    KnowledgeTag,
)
from app.schemas.typings.knowledge.prefixed_id import KnowledgeItemId
from app.schemas.typings.knowledge.strings import KnowledgeBody, KnowledgeTitle
from app.schemas.typings.localization.constrained_strings import (
    CurrencyCode,
    LanguageTag,
)
from app.schemas.typings.users.prefixed_id import UserId


class BrandMember(PersistentDocument):
    """
    A person of a brand's team. A REGIONAL_MANAGER works only in the
    locations of `business_ids` that still belong to the brand; a
    BRAND_OWNER works in every location and keeps the list empty.
    """

    user_id: UserId
    role: BrandMemberRole
    business_ids: list[BusinessId] = Field(default_factory=list[BusinessId])


class BrandDocument(BaseDocument):
    """
    A chain of locations run by one team (R17-BRANDS; collection `brands`,
    platform-wide). Which businesses belong to it is said by each
    business (`BusinessDocument.brand_id`), the one source of truth: a
    brand member reaches a location only while both agree.

    `setup_fee_business_id` is the location that carries the brand's one
    setup fee (claimed by the first location invoiced one); the brand's
    other locations are never charged it.
    """

    schema_version: SchemaVersion = SchemaVersion("1")
    id: BrandId = Field(default_factory=BrandId)
    name: BrandName
    members: list[BrandMember]
    setup_fee_business_id: BusinessId | None = None


class BrandKnowledgeItemDocument(BaseDocument):
    """
    A fact every location of a brand shares (collection
    `brand_knowledge_items`, platform-wide, keyed by brand and
    `shared_key`): a FAQ, a policy, a menu item or a product. A
    location's own knowledge item with the same `shared_key` replaces it
    in that location's assistant, an inactive one hides it there. The id
    is a knowledge item id: the location's assistant reads the item as one
    of its own knowledge items, never stored in the location.

    A price is in `currency_code`; a location keeping another currency
    gets the item without it.
    """

    schema_version: SchemaVersion = SchemaVersion("1")
    id: KnowledgeItemId = Field(default_factory=KnowledgeItemId)
    brand_id: BrandId
    shared_key: KnowledgeShareKey
    kind: KnowledgeItemKind
    title: KnowledgeTitle
    body: KnowledgeBody | None = None
    price_minor: MoneyAmountMinor | None = None
    currency_code: CurrencyCode | None = None
    tags: list[KnowledgeTag] = Field(default_factory=list[KnowledgeTag])
    languages: list[LanguageTag] = Field(default_factory=list[LanguageTag])
    is_active: IsKnowledgeItemActive = True
