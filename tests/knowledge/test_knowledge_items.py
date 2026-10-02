"""
Creating knowledge items: prices in the business currency, niche checks, bad input.
"""

import pytest

from app.schemas.constants.knowledge import KnowledgeItemKind, KnowledgeItemSource
from app.schemas.constants.niches import NicheKey
from app.schemas.domain.knowledge import KnowledgeAttribute
from app.schemas.dto.knowledge_admin import (
    CreateKnowledgeItemCommand,
    KnowledgeItemInput,
)
from app.schemas.exceptions.application_errors import ValidationFailedError
from app.schemas.typings.billing.constrained_integers import MoneyAmountMinor
from app.schemas.typings.knowledge.constrained_integers import ServiceDurationMinutes
from app.schemas.typings.knowledge.constrained_strings import (
    KnowledgeAttributeKey,
    KnowledgeTag,
)
from app.schemas.typings.knowledge.strings import (
    KnowledgeAttributeValue,
    KnowledgeBody,
    KnowledgeTitle,
)
from app.schemas.typings.localization.constrained_strings import (
    CurrencyCode,
    LanguageTag,
)
from tests.knowledge.harness import KnowledgeHarness
from tests.knowledge.knowledge_base_helpers import add_item


@pytest.mark.parametrize(
    ("country", "currency", "timezone", "language", "price_minor", "expected"),
    [
        ("GE", "GEL", "Asia/Tbilisi", "ka", 1850, "18,50\xa0₾"),
        ("IT", "EUR", "Europe/Rome", "it", 1250, "12,50\xa0€"),
        ("JP", "JPY", "Asia/Tokyo", "ja", 1500, "￥1,500"),
    ],
)
def test_prices_are_stored_and_formatted_in_the_business_currency(
    country: str,
    currency: str,
    timezone: str,
    language: str,
    price_minor: int,
    expected: str,
) -> None:
    harness = KnowledgeHarness()
    business = harness.add_business(
        country_code=country,
        currency_code=currency,
        timezone=timezone,
        languages=(language, "en"),
        owner_language=language,
    )

    details = add_item(harness, business, "Dish", price_minor=price_minor)

    assert details.price_minor == price_minor
    assert details.currency_code == currency
    assert details.formatted_price == expected
    assert details.source is KnowledgeItemSource.OWNER
    assert details.created_at == harness.wall_clock.now_unix()


@pytest.mark.parametrize("foreign_currency", ["USD", "EUR", "JPY"])
def test_prices_in_another_currency_are_rejected(foreign_currency: str) -> None:
    harness = KnowledgeHarness()
    business = harness.add_business()

    with pytest.raises(ValidationFailedError, match="business currency GEL"):
        harness.create_knowledge_item.run(
            CreateKnowledgeItemCommand(
                business_id=business.id,
                item=KnowledgeItemInput(
                    kind=KnowledgeItemKind.MENU_ITEM,
                    title=KnowledgeTitle("Khachapuri"),
                    price_minor=MoneyAmountMinor(1800),
                    currency_code=CurrencyCode(foreign_currency),
                ),
            )
        )


def test_items_are_checked_against_the_niche_and_kept_as_written() -> None:
    harness = KnowledgeHarness()
    business = harness.add_business(niche_key=NicheKey.HOTEL)

    details = harness.create_knowledge_item.run(
        CreateKnowledgeItemCommand(
            business_id=business.id,
            item=KnowledgeItemInput(
                kind=KnowledgeItemKind.ROOM_TYPE,
                title=KnowledgeTitle("  Double room  "),
                body=KnowledgeBody("   "),
                price_minor=MoneyAmountMinor(25000),
                currency_code=CurrencyCode("GEL"),
                duration_minutes=ServiceDurationMinutes(1440),
                tags=[KnowledgeTag("sea-view"), KnowledgeTag("sea-view")],
                attributes=[
                    KnowledgeAttribute(
                        key=KnowledgeAttributeKey("season"),
                        value=KnowledgeAttributeValue(" summer "),
                    )
                ],
                languages=[LanguageTag("en"), LanguageTag("en")],
            ),
            language=LanguageTag("ru"),
        )
    )

    assert details.title == "  Double room  "
    assert details.body is None
    assert details.tags == ["sea-view"]
    assert details.attributes[0].value == " summer "
    assert details.languages == ["en"]
    assert details.formatted_price == "250,00\xa0GEL"

    with pytest.raises(ValidationFailedError, match="does not use menu_item"):
        add_item(harness, business, "Khachapuri", kind=KnowledgeItemKind.MENU_ITEM)

    faq = add_item(harness, business, "Pets?", kind=KnowledgeItemKind.FAQ)
    assert faq.kind is KnowledgeItemKind.FAQ


@pytest.mark.parametrize(
    ("item_input", "message"),
    [
        (
            KnowledgeItemInput(kind=KnowledgeItemKind.FAQ, title=KnowledgeTitle("  ")),
            "needs a title",
        ),
        (
            KnowledgeItemInput(
                kind=KnowledgeItemKind.FAQ,
                title=KnowledgeTitle("x" * 301),
            ),
            "at most 300",
        ),
        (
            KnowledgeItemInput(
                kind=KnowledgeItemKind.FAQ,
                title=KnowledgeTitle("Parking"),
                attributes=[
                    KnowledgeAttribute(
                        key=KnowledgeAttributeKey("floor"),
                        value=KnowledgeAttributeValue("1"),
                    ),
                    KnowledgeAttribute(
                        key=KnowledgeAttributeKey("floor"),
                        value=KnowledgeAttributeValue("2"),
                    ),
                ],
            ),
            "repeated",
        ),
        (
            KnowledgeItemInput(
                kind=KnowledgeItemKind.FAQ,
                title=KnowledgeTitle("Parking"),
                attributes=[
                    KnowledgeAttribute(
                        key=KnowledgeAttributeKey("floor"),
                        value=KnowledgeAttributeValue(" "),
                    )
                ],
            ),
            "needs a value",
        ),
    ],
)
def test_invalid_items_are_rejected(
    item_input: KnowledgeItemInput, message: str
) -> None:
    harness = KnowledgeHarness()
    business = harness.add_business()

    with pytest.raises(ValidationFailedError, match=message):
        harness.create_knowledge_item.run(
            CreateKnowledgeItemCommand(business_id=business.id, item=item_input)
        )
