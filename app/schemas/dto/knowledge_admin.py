"""Owner-side management of the knowledge base (cabinet page /knowledge).

Prices are integers in minor units of the business currency (tetri, cents,
yen). A price in another currency is rejected, so the assistant can never
quote an amount the business did not set in its own currency.
"""

from base_pydantic_schemas import ImmutableDTO
from pydantic import Field
from typed_time_provider import Microseconds

from app.schemas.constants.knowledge import KnowledgeItemKind, KnowledgeItemSource
from app.schemas.domain.knowledge import KnowledgeAttribute
from app.schemas.typings.billing.constrained_integers import MoneyAmountMinor
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.knowledge.booleans import IsKnowledgeItemActive
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


class KnowledgeItemInput(ImmutableDTO):
    """
    A new knowledge item (menu dish, service, room type, package, FAQ, rule).

    `currency_code` may be omitted: prices are always in the business
    currency, and a different code is rejected.
    """

    kind: KnowledgeItemKind
    title: KnowledgeTitle
    body: KnowledgeBody | None = None
    price_minor: MoneyAmountMinor | None = None
    currency_code: CurrencyCode | None = None
    duration_minutes: ServiceDurationMinutes | None = None
    tags: list[KnowledgeTag] = Field(default_factory=list[KnowledgeTag])
    attributes: list[KnowledgeAttribute] = Field(
        default_factory=list[KnowledgeAttribute]
    )
    languages: list[LanguageTag] = Field(default_factory=list[LanguageTag])
    is_active: IsKnowledgeItemActive = True


class KnowledgeItemUpsertInput(KnowledgeItemInput):
    """
    A knowledge item to create or update in a bulk upsert.

    An item with `id` updates that item; without `id` it updates the item of
    the same kind and title (ignoring case and accents) or creates a new one,
    so saving the same wizard step twice does not duplicate items.
    """

    id: KnowledgeItemId | None = None


class KnowledgeItemPatch(ImmutableDTO):
    """
    Partial update of a knowledge item.

    Only fields present in the request change; an explicit null clears an
    optional field (body, price, duration). `is_active` switches the item on
    or off for the assistant without deleting it.
    """

    kind: KnowledgeItemKind | None = None
    title: KnowledgeTitle | None = None
    body: KnowledgeBody | None = None
    price_minor: MoneyAmountMinor | None = None
    currency_code: CurrencyCode | None = None
    duration_minutes: ServiceDurationMinutes | None = None
    tags: list[KnowledgeTag] | None = None
    attributes: list[KnowledgeAttribute] | None = None
    languages: list[LanguageTag] | None = None
    is_active: IsKnowledgeItemActive | None = None


class CreateKnowledgeItemCommand(ImmutableDTO):
    """Add one item; `language` formats the returned price (owner language)."""

    business_id: BusinessId
    item: KnowledgeItemInput
    source: KnowledgeItemSource = KnowledgeItemSource.OWNER
    language: LanguageTag | None = None


class UpdateKnowledgeItemCommand(ImmutableDTO):
    """Change one item of the business."""

    business_id: BusinessId
    item_id: KnowledgeItemId
    patch: KnowledgeItemPatch
    language: LanguageTag | None = None


class DeleteKnowledgeItemCommand(ImmutableDTO):
    """Delete one item of the business."""

    business_id: BusinessId
    item_id: KnowledgeItemId


class UpsertKnowledgeItemsCommand(ImmutableDTO):
    """Create or update many items at once (wizard offer and FAQ steps)."""

    business_id: BusinessId
    items: list[KnowledgeItemUpsertInput]
    source: KnowledgeItemSource = KnowledgeItemSource.PROFILE
    language: LanguageTag | None = None


class KnowledgeItemQuery(ImmutableDTO):
    """Read one item of the business."""

    business_id: BusinessId
    item_id: KnowledgeItemId
    language: LanguageTag | None = None


class KnowledgeItemListQuery(ImmutableDTO):
    """
    List items of the business, optionally filtered.

    `is_active` None lists active and inactive items.
    """

    business_id: BusinessId
    kind: KnowledgeItemKind | None = None
    is_active: IsKnowledgeItemActive | None = None
    language: LanguageTag | None = None


class KnowledgeSearchInput(ImmutableDTO):
    """
    Search request from the cabinet; the business comes from the URL.

    `language` defaults to the owner's language.
    """

    query: KnowledgeSearchQuery
    language: LanguageTag | None = None
    limit: KnowledgeSearchLimit = KnowledgeSearchLimit(5)


class KnowledgeItemDetails(ImmutableDTO):
    """A knowledge item as the owner sees it, with the price formatted."""

    id: KnowledgeItemId
    business_id: BusinessId
    kind: KnowledgeItemKind
    title: KnowledgeTitle
    body: KnowledgeBody | None = None
    price_minor: MoneyAmountMinor | None = None
    currency_code: CurrencyCode | None = None
    formatted_price: FormattedMoneyText | None = None
    duration_minutes: ServiceDurationMinutes | None = None
    tags: list[KnowledgeTag] = Field(default_factory=list[KnowledgeTag])
    attributes: list[KnowledgeAttribute] = Field(
        default_factory=list[KnowledgeAttribute]
    )
    languages: list[LanguageTag] = Field(default_factory=list[LanguageTag])
    source: KnowledgeItemSource
    is_active: IsKnowledgeItemActive
    created_at: Microseconds
    updated_at: Microseconds


class KnowledgeItemList(ImmutableDTO):
    """Items of one business, grouped by kind and ordered by title."""

    items: list[KnowledgeItemDetails] = Field(
        default_factory=list[KnowledgeItemDetails]
    )


class KnowledgeItemDeletion(ImmutableDTO):
    """Identifier of the deleted item."""

    id: KnowledgeItemId
