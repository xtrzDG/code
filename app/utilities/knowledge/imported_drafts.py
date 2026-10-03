"""
Knowledge item drafts made by an import (a menu, a price list, a website):
switched off until the owner confirms them, with the reader's confidence,
and the printed price kept aside when its currency is not the business's.
"""

from decimal import Decimal

from typed_time_provider import Microseconds

from app.schemas.constants.knowledge import KnowledgeItemSource
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.domain.knowledge import KnowledgeAttribute, KnowledgeItemDocument
from app.schemas.dto.menu_import import ExtractedMenuItem
from app.schemas.typings.billing.constrained_integers import MoneyAmountMinor
from app.schemas.typings.knowledge.strings import KnowledgeAttributeValue
from app.schemas.typings.localization.constrained_strings import CurrencyCode
from app.schemas.typings.menu_import.prefixed_id import MenuImportBatchId
from app.utilities.knowledge.imported_item_views import (
    CONFIDENCE_ATTRIBUTE,
    PRINTED_CURRENCY_ATTRIBUTE,
    PRINTED_PRICE_ATTRIBUTE,
)
from app.utilities.money.money_math import build_money_from_major_units


def build_draft(
    business: BusinessDocument,
    extracted_item: ExtractedMenuItem,
    batch_id: MenuImportBatchId,
    now: Microseconds,
) -> KnowledgeItemDocument:
    printed_currency: CurrencyCode = (
        extracted_item.currency_code
        if extracted_item.currency_code is not None
        else business.currency_code
    )
    is_currency_mismatch: bool = (
        extracted_item.price is not None and printed_currency != business.currency_code
    )
    attributes: list[KnowledgeAttribute] = [
        KnowledgeAttribute(
            key=CONFIDENCE_ATTRIBUTE,
            value=KnowledgeAttributeValue(f"{float(extracted_item.confidence):.2f}"),
        )
    ]
    price_minor: MoneyAmountMinor | None = None
    if extracted_item.price is not None and not is_currency_mismatch:
        price_minor = build_money_from_major_units(
            Decimal(str(extracted_item.price)),
            business.currency_code,
        ).amount_minor
    elif extracted_item.price is not None:
        attributes.extend(
            [
                KnowledgeAttribute(
                    key=PRINTED_PRICE_ATTRIBUTE,
                    value=KnowledgeAttributeValue(str(extracted_item.price)),
                ),
                KnowledgeAttribute(
                    key=PRINTED_CURRENCY_ATTRIBUTE,
                    value=KnowledgeAttributeValue(str(printed_currency)),
                ),
            ]
        )

    return KnowledgeItemDocument(
        business_id=business.id,
        kind=extracted_item.kind,
        title=extracted_item.title,
        body=extracted_item.body,
        price_minor=price_minor,
        currency_code=None if price_minor is None else business.currency_code,
        duration_minutes=extracted_item.duration_minutes,
        tags=list(extracted_item.tags),
        attributes=attributes,
        source=KnowledgeItemSource.MENU_IMPORT,
        is_active=False,
        import_batch_id=batch_id,
        created_at=now,
        updated_at=now,
    )
