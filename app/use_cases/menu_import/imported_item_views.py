"""Views of imported knowledge items, shared by the menu import use cases."""

from decimal import Decimal

from app.schemas.domain.knowledge import KnowledgeItemDocument
from app.schemas.dto.billing import Money
from app.schemas.dto.knowledge import KnowledgeItemView
from app.schemas.dto.menu_import import ImportedMenuItemView
from app.schemas.exceptions.application_errors import UnsupportedLanguageError
from app.schemas.typings.knowledge.constrained_strings import KnowledgeAttributeKey
from app.schemas.typings.localization.constrained_strings import (
    CurrencyCode,
    LanguageTag,
)
from app.schemas.typings.localization.strings import FormattedMoneyText
from app.schemas.typings.menu_import.constrained_floats import ExtractionConfidence
from app.schemas.typings.menu_import.constrained_strings import ExtractedPriceAmount
from app.utilities.money.money_formatting import format_money

CONFIDENCE_ATTRIBUTE: KnowledgeAttributeKey = KnowledgeAttributeKey("import_confidence")
PRINTED_PRICE_ATTRIBUTE: KnowledgeAttributeKey = KnowledgeAttributeKey("printed_price")
PRINTED_CURRENCY_ATTRIBUTE: KnowledgeAttributeKey = KnowledgeAttributeKey(
    "printed_currency"
)


def build_knowledge_item_view(
    item: KnowledgeItemDocument,
    display_language: LanguageTag,
) -> KnowledgeItemView:
    """Item with its price formatted for the owner's language."""

    formatted_price: FormattedMoneyText | None = None
    if item.price_minor is not None and item.currency_code is not None:
        try:
            formatted_price = format_money(
                Money(amount_minor=item.price_minor, currency_code=item.currency_code),
                display_language,
            )
        except UnsupportedLanguageError:
            formatted_price = None

    return KnowledgeItemView(
        id=item.id,
        kind=item.kind,
        title=item.title,
        body=item.body,
        price_minor=item.price_minor,
        currency_code=item.currency_code,
        formatted_price=formatted_price,
        duration_minutes=item.duration_minutes,
        tags=list(item.tags),
    )


def build_imported_item_view(
    item: KnowledgeItemDocument,
    display_language: LanguageTag,
) -> ImportedMenuItemView:
    """Draft with the confidence and printed price kept in its attributes."""

    attributes: dict[str, str] = {
        str(attribute.key): str(attribute.value) for attribute in item.attributes
    }
    printed_price: str | None = attributes.get(str(PRINTED_PRICE_ATTRIBUTE))
    printed_currency: str | None = attributes.get(str(PRINTED_CURRENCY_ATTRIBUTE))
    return ImportedMenuItemView(
        item=build_knowledge_item_view(item, display_language),
        confidence=ExtractionConfidence(
            float(Decimal(attributes.get(str(CONFIDENCE_ATTRIBUTE), "0")))
        ),
        is_currency_mismatch=printed_currency is not None,
        printed_price=None
        if printed_price is None
        else ExtractedPriceAmount(printed_price),
        printed_currency_code=(
            None if printed_currency is None else CurrencyCode(printed_currency)
        ),
    )
