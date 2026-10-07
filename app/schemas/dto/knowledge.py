from base_pydantic_schemas import ImmutableDTO
from pydantic import Field

from app.schemas.constants.businesses import BusinessLinkKind
from app.schemas.constants.knowledge import KnowledgeItemKind
from app.schemas.domain.knowledge import SeasonalNightlyRate
from app.schemas.dto.bookable_offers import StayQuote
from app.schemas.typings.billing.constrained_integers import MoneyAmountMinor
from app.schemas.typings.bookings.constrained_integers import NightCount
from app.schemas.typings.bookings.constrained_strings import LocalDate
from app.schemas.typings.businesses.constrained_strings import WebLink
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.knowledge.constrained_integers import (
    BufferMinutes,
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
    """
    Knowledge item as shown to the model or the owner; a room type carries
    its seasonal nightly rates (`price_minor` outside the seasons).
    """

    id: KnowledgeItemId
    kind: KnowledgeItemKind
    title: KnowledgeTitle
    body: KnowledgeBody | None = None
    price_minor: MoneyAmountMinor | None = None
    currency_code: CurrencyCode | None = None
    formatted_price: FormattedMoneyText | None = None
    duration_minutes: ServiceDurationMinutes | None = None
    buffer_minutes: BufferMinutes | None = None
    seasonal_rates: list[SeasonalNightlyRate] = Field(
        default_factory=list[SeasonalNightlyRate]
    )
    tags: list[KnowledgeTag] = Field(default_factory=list[KnowledgeTag])


class KnowledgeSearchResult(ImmutableDTO):
    """Up to `limit` matching items, best first."""

    items: list[KnowledgeItemView] = Field(default_factory=list[KnowledgeItemView])


class PriceLookupQuery(ImmutableDTO):
    """
    Look up a price by item name (concept get_price). With a check-in date
    (and nights, one by default) a matching room type is quoted for the
    stay: each night at its season's rate.
    """

    business_id: BusinessId
    item_name: KnowledgeTitle
    language: LanguageTag
    check_in: LocalDate | None = None
    nights: NightCount | None = None


class PriceLookupResult(ImmutableDTO):
    """
    Matching priced items. Empty `matches` means "not in the price list":
    the assistant may then name no price at all.
    """

    matches: list[KnowledgeItemView] = Field(default_factory=list[KnowledgeItemView])
    stay_quotes: list[StayQuote] = Field(default_factory=list[StayQuote])


class SendLinkQuery(ImmutableDTO):
    """Ask for a link from the profile (concept send_link)."""

    business_id: BusinessId
    kind: BusinessLinkKind


class SendLinkResult(ImmutableDTO):
    """The profile link, or None when the profile has no such link."""

    kind: BusinessLinkKind
    url: WebLink | None = None
