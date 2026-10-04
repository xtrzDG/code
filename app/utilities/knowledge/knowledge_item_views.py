"""A knowledge item as the language model and as the owner see it."""

from collections.abc import Sequence

from app.schemas.constants.knowledge import KnowledgeItemSource
from app.schemas.domain.knowledge import KnowledgeItemDocument
from app.schemas.domain.resources import ResourceDocument
from app.schemas.dto.knowledge import KnowledgeItemView
from app.schemas.dto.knowledge_admin import KnowledgeItemDetails
from app.schemas.typings.localization.constrained_strings import (
    CurrencyCode,
    LanguageTag,
)
from app.schemas.typings.localization.strings import FormattedMoneyText
from app.utilities.bookings.offer_links import linked_performer_ids
from app.utilities.knowledge.money_formatting import format_money_minor


def format_item_price(
    item: KnowledgeItemDocument,
    fallback_currency_code: CurrencyCode,
    language: LanguageTag,
) -> FormattedMoneyText | None:
    """The price in the item's currency, formatted for `language`."""

    if item.price_minor is None:
        return None

    currency_code: CurrencyCode = (
        item.currency_code if item.currency_code is not None else fallback_currency_code
    )
    return format_money_minor(item.price_minor, currency_code, language)


def to_item_view(
    item: KnowledgeItemDocument,
    fallback_currency_code: CurrencyCode,
    language: LanguageTag,
) -> KnowledgeItemView:
    """The item as the language model sees it (search_knowledge, get_price)."""

    return KnowledgeItemView(
        id=item.id,
        kind=item.kind,
        title=item.title,
        body=item.body,
        price_minor=item.price_minor,
        currency_code=(
            None
            if item.price_minor is None
            else item.currency_code or fallback_currency_code
        ),
        formatted_price=format_item_price(item, fallback_currency_code, language),
        duration_minutes=item.duration_minutes,
        buffer_minutes=item.buffer_minutes,
        seasonal_rates=list(item.seasonal_rates),
        tags=list(item.tags),
        is_imported=item.source is KnowledgeItemSource.MENU_IMPORT,
    )


def to_item_details(
    item: KnowledgeItemDocument,
    fallback_currency_code: CurrencyCode,
    language: LanguageTag,
    resources: Sequence[ResourceDocument] = (),
) -> KnowledgeItemDetails:
    """
    The item as the owner sees it in the cabinet, with every resource that
    performs it (linked from either side) when the resources are given.
    """

    return KnowledgeItemDetails(
        id=item.id,
        business_id=item.business_id,
        kind=item.kind,
        title=item.title,
        body=item.body,
        price_minor=item.price_minor,
        currency_code=item.currency_code,
        formatted_price=format_item_price(item, fallback_currency_code, language),
        duration_minutes=item.duration_minutes,
        buffer_minutes=item.buffer_minutes,
        performer_resource_ids=linked_performer_ids(item, resources),
        seasonal_rates=list(item.seasonal_rates),
        tags=list(item.tags),
        attributes=list(item.attributes),
        languages=list(item.languages),
        source=item.source,
        is_active=item.is_active,
        created_at=item.created_at,
        updated_at=item.updated_at,
    )
