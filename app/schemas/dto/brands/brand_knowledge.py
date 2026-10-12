"""The knowledge a brand's locations share, and its location overrides."""

from base_pydantic_schemas import ImmutableDTO
from pydantic import Field
from typed_time_provider import Microseconds

from app.schemas.constants.knowledge import KnowledgeItemKind
from app.schemas.typings.billing.constrained_integers import MoneyAmountMinor
from app.schemas.typings.brands.prefixed_id import BrandId
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.compliance.strings import ClientIpAddress
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


class BrandKnowledgeItemRequest(ImmutableDTO):
    """
    A fact every location of the brand shares: a FAQ, a policy, a menu
    item or a product. A price is in the currency of the brand's
    locations (they must share one). `shared_key` names the item for the
    locations that replace it with their own (made from the kind when
    omitted on creation; it never changes afterwards).

    Example: {"kind": "faq", "title": "Parking", "body": "Free after 18:00."}.
    """

    kind: KnowledgeItemKind
    title: KnowledgeTitle
    body: KnowledgeBody | None = None
    price_minor: MoneyAmountMinor | None = None
    tags: list[KnowledgeTag] = Field(default_factory=list[KnowledgeTag])
    languages: list[LanguageTag] = Field(default_factory=list[LanguageTag])
    is_active: IsKnowledgeItemActive = True
    shared_key: KnowledgeShareKey | None = None


class BrandKnowledgeItemView(ImmutableDTO):
    """
    A shared fact and the locations (of those the viewer reaches) whose
    own item with its key replaces it (`overridden_in`).
    """

    id: KnowledgeItemId
    shared_key: KnowledgeShareKey
    kind: KnowledgeItemKind
    title: KnowledgeTitle
    body: KnowledgeBody | None = None
    price_minor: MoneyAmountMinor | None = None
    currency_code: CurrencyCode | None = None
    tags: list[KnowledgeTag] = Field(default_factory=list[KnowledgeTag])
    languages: list[LanguageTag] = Field(default_factory=list[LanguageTag])
    is_active: IsKnowledgeItemActive
    overridden_in: list[BusinessId] = Field(default_factory=list[BusinessId])
    updated_at: Microseconds


class BrandKnowledgeList(ImmutableDTO):
    """A brand's shared facts, oldest first."""

    items: list[BrandKnowledgeItemView] = Field(
        default_factory=list[BrandKnowledgeItemView]
    )


class BrandKnowledgeCommand(ImmutableDTO):
    """A brand owner adds a shared fact."""

    user_id: UserId
    brand_id: BrandId
    request: BrandKnowledgeItemRequest


class BrandKnowledgeItemCommand(ImmutableDTO):
    """A brand owner changes (`request`) or removes (None) a shared fact."""

    user_id: UserId
    brand_id: BrandId
    shared_key: KnowledgeShareKey
    request: BrandKnowledgeItemRequest | None = None


class LocationOverridesQuery(ImmutableDTO):
    """Which shared facts one location replaces, for a member who reaches it."""

    user_id: UserId
    business_id: BusinessId


class LocationOverrides(ImmutableDTO):
    business_id: BusinessId
    shared_keys: list[KnowledgeShareKey] = Field(
        default_factory=list[KnowledgeShareKey]
    )


class OverrideBrandKnowledgeRequest(ImmutableDTO):
    """The shared fact this location replaces with its own copy to edit."""

    shared_key: KnowledgeShareKey


class OverrideBrandKnowledgeCommand(ImmutableDTO):
    user_id: UserId
    business_id: BusinessId
    request: OverrideBrandKnowledgeRequest
    client_ip_address: ClientIpAddress | None = None
