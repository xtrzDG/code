"""
A location's own item with a shared fact's key replaces the brand's fact
there; an inactive one hides it; every other active fact is added, and a
shared price in another currency never reaches the location.
"""

from app.schemas.constants.knowledge import KnowledgeItemKind
from app.schemas.domain.knowledge import KnowledgeItemDocument
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.knowledge.constrained_strings import KnowledgeShareKey
from app.schemas.typings.knowledge.strings import KnowledgeTitle
from app.schemas.typings.users.prefixed_id import UserId
from app.utilities.brands.brand_knowledge_merge import merge_brand_knowledge
from tests.brands.brand_builders import (
    build_brand,
    build_location,
    build_shared_fact,
)

OWNER = UserId()


def own_item(
    location_id: BusinessId, key: str | None, title: str, is_active: bool = True
) -> KnowledgeItemDocument:
    return KnowledgeItemDocument(
        business_id=location_id,
        kind=KnowledgeItemKind.FAQ,
        title=KnowledgeTitle(title),
        shared_key=None if key is None else KnowledgeShareKey(key),
        is_active=is_active,
    )


def titles(items: list[KnowledgeItemDocument]) -> list[str]:
    return [str(item.title) for item in items if item.is_active]


def test_a_location_item_with_the_same_key_overrides_the_shared_fact() -> None:
    brand = build_brand(OWNER)
    location = build_location(brand, OWNER)
    shared = [
        build_shared_fact(brand, "parking", "Parking (brand)"),
        build_shared_fact(brand, "wifi", "Wi-Fi (brand)"),
    ]
    own = [own_item(location.id, "parking", "Parking (Vake)")]

    merged = merge_brand_knowledge(own, shared, location)

    assert titles(merged) == ["Parking (Vake)", "Wi-Fi (brand)"]


def test_an_inactive_location_item_hides_the_shared_fact() -> None:
    brand = build_brand(OWNER)
    location = build_location(brand, OWNER)
    shared = [build_shared_fact(brand, "terrace", "Terrace")]
    own = [own_item(location.id, "terrace", "No terrace here", is_active=False)]

    assert titles(merge_brand_knowledge(own, shared, location)) == []


def test_inactive_shared_facts_and_unkeyed_items_keep_their_place() -> None:
    brand = build_brand(OWNER)
    location = build_location(brand, OWNER)
    shared = [build_shared_fact(brand, "kids", "Kids menu", is_active=False)]
    own = [own_item(location.id, None, "Opening hours")]

    assert titles(merge_brand_knowledge(own, shared, location)) == ["Opening hours"]


def test_a_shared_price_in_another_currency_is_left_out() -> None:
    brand = build_brand(OWNER)
    location = build_location(brand, OWNER)  # Keeps EUR.
    shared = [
        build_shared_fact(brand, "khachapuri", "Khachapuri", 1800, "GEL"),
        build_shared_fact(brand, "espresso", "Espresso", 250, "EUR"),
    ]

    merged = {
        str(item.title): item for item in merge_brand_knowledge([], shared, location)
    }

    assert merged["Khachapuri"].price_minor is None
    assert merged["Khachapuri"].currency_code is None
    assert merged["Espresso"].price_minor == 250
    assert merged["Espresso"].business_id == location.id
