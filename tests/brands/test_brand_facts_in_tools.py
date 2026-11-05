"""
The assistant's knowledge tools answer a brand's location with its own
items and the facts its brand shares (search_knowledge, get_price): a
location item with the shared key replaces the fact, and a shared price
in another currency than the location's is never quoted.
"""

from app.schemas.constants.knowledge import KnowledgeItemKind
from app.schemas.domain.brands import BrandDocument
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.domain.knowledge import KnowledgeItemDocument
from app.schemas.dto.knowledge import KnowledgeSearchRequest, PriceLookupQuery
from app.schemas.typings.knowledge.constrained_strings import KnowledgeShareKey
from app.schemas.typings.knowledge.strings import (
    KnowledgeBody,
    KnowledgeSearchQuery,
    KnowledgeTitle,
)
from app.schemas.typings.localization.constrained_strings import LanguageTag
from tests.brands.brand_builders import build_brand, build_shared_fact
from tests.knowledge.harness import KnowledgeHarness

ENGLISH: LanguageTag = LanguageTag("en")


def brand_location(harness: KnowledgeHarness) -> tuple[BusinessDocument, BrandDocument]:
    """A Tbilisi location (GEL) of a brand that shares parking, a dish in
    GEL and a dish priced in EUR."""

    business = harness.add_business()
    brand = build_brand(business.members[0].user_id)
    located = business.model_copy(update={"brand_id": brand.id})
    harness.business_repo.save(located)
    for shared in (
        build_shared_fact(brand, "parking", "Parking"),
        build_shared_fact(brand, "lobiani", "Lobiani", 900, "GEL"),
        build_shared_fact(brand, "strudel", "Apple strudel", 650, "EUR"),
    ):
        dish = shared.price_minor is not None
        harness.brand_knowledge_repo.add(
            shared.model_copy(update={"kind": KnowledgeItemKind.MENU_ITEM})
            if dish
            else shared
        )
    return located, brand


def search(
    harness: KnowledgeHarness, business: BusinessDocument, text: str
) -> list[str]:
    result = harness.search_knowledge.run(
        KnowledgeSearchRequest(
            business_id=business.id,
            query=KnowledgeSearchQuery(text),
            language=ENGLISH,
        )
    )
    return [str(item.body) for item in result.items]


def prices(
    harness: KnowledgeHarness, business: BusinessDocument, name: str
) -> list[int]:
    result = harness.get_price.run(
        PriceLookupQuery(
            business_id=business.id, item_name=KnowledgeTitle(name), language=ENGLISH
        )
    )
    return [int(item.price_minor or 0) for item in result.matches]


def test_search_finds_the_shared_fact_and_then_the_location_s_own() -> None:
    harness = KnowledgeHarness()
    business, _ = brand_location(harness)
    shared_answer = search(harness, business, "parking")
    harness.knowledge_item_repo.save(
        KnowledgeItemDocument(
            business_id=business.id,
            kind=KnowledgeItemKind.FAQ,
            title=KnowledgeTitle("Parking"),
            body=KnowledgeBody("Valet parking only."),
            shared_key=KnowledgeShareKey("parking"),
        )
    )

    own_answer = search(harness, business, "parking")

    assert shared_answer == ["Parking: the brand's answer."]
    assert own_answer == ["Valet parking only."]


def test_get_price_quotes_shared_prices_in_the_location_s_currency_only() -> None:
    harness = KnowledgeHarness()
    business, _ = brand_location(harness)
    outsider = harness.add_business()

    assert prices(harness, business, "lobiani") == [900]
    assert prices(harness, business, "apple strudel") == []
    assert prices(harness, outsider, "lobiani") == []
    assert search(harness, outsider, "parking") == []
