from base_pydantic_schemas import ImmutableDTO
from pydantic import Field

from app.schemas.constants.businesses import BusinessLinkKind
from app.schemas.constants.knowledge import KnowledgeItemKind
from app.schemas.typings.billing.constrained_integers import MoneyAmountMinor
from app.schemas.typings.businesses.constrained_strings import WebLink
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.knowledge.constrained_integers import (
    KnowledgeSearchLimit,
    ServiceDurationMinutes,
)
from app.schemas.typings.knowledge.constrained_strings import KnowledgeTag
from app.schemas.typings.knowledge.prefixed_id import KnowledgeItemId
from app.schemas.typings.knowledge.strings import (
    KnowledgeBody,
    KnowledgeSearchQuery,
    KnowledgeTitle,
)
from app.schemas.typings.localization.constrained_strings import (
    CurrencyCode,
    LanguageTag,
)
from app.schemas.typings.localization.strings import FormattedMoneyText


class KnowledgeSearchRequest(ImmutableDTO):
    """Search the business knowledge base (concept search_knowledge)."""

    business_id: BusinessId
    query: KnowledgeSearchQuery
    language: LanguageTag
    limit: KnowledgeSearchLimit = KnowledgeSearchLimit(5)


class KnowledgeItemView(ImmutableDTO):
    """Knowledge item as shown to the model or the owner."""

    id: KnowledgeItemId
    kind: KnowledgeItemKind
    title: KnowledgeTitle
    body: KnowledgeBody | None = None
    price_minor: MoneyAmountMinor | None = None
    currency_code: CurrencyCode | None = None
    formatted_price: FormattedMoneyText | None = None
    duration_minutes: ServiceDurationMinutes | None = None
    tags: list[KnowledgeTag] = Field(default_factory=list[KnowledgeTag])


class KnowledgeSearchResult(ImmutableDTO):
    """Up to `limit` matching items, best first."""

    items: list[KnowledgeItemView] = Field(default_factory=list[KnowledgeItemView])


class PriceLookupQuery(ImmutableDTO):
    """Look up a price by item name (concept get_price)."""

    business_id: BusinessId
    item_name: KnowledgeTitle
    language: LanguageTag


class PriceLookupResult(ImmutableDTO):
    """
    Matching priced items. Empty `matches` means "not in the price list":
    the assistant may then name no price at all.
    """

    matches: list[KnowledgeItemView] = Field(default_factory=list[KnowledgeItemView])


class SendLinkQuery(ImmutableDTO):
    """Ask for a link from the profile (concept send_link)."""

    business_id: BusinessId
    kind: BusinessLinkKind


class SendLinkResult(ImmutableDTO):
    """The profile link, or None when the profile has no such link."""

    kind: BusinessLinkKind
    url: WebLink | None = None
