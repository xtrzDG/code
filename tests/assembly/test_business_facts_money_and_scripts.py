"""Facts in other currencies and scripts: euros, yen, right-to-left texts."""

from app.schemas.constants.knowledge import KnowledgeItemKind
from app.transformers.assembly.business_facts_transformer import (
    BusinessFactsTransformer,
)
from tests.assembly.builders import build_menu_item
from tests.assembly.business_facts_helpers import as_table, build_source
from tests.assembly.international_business_seeds import (
    seed_israeli_clinic,
    seed_italian_restaurant,
    seed_japanese_restaurant,
    seed_online_shop,
)
from tests.assembly.testbed import AssemblyTestbed


def test_italian_prices_are_in_euros_with_cents() -> None:
    testbed = AssemblyTestbed()
    business = seed_italian_restaurant(testbed)

    table = as_table(
        BusinessFactsTransformer().transform(build_source(testbed, business))
    )

    assert table["menu_item_1"] == ("Menu item: Pizza Margherita", "Price: 8.50 EUR")
    assert table["menu_item_2"] == (
        "Menu item: Tiramisù",
        "Price: 6.00 EUR; Tags: dessert",
    )
    assert table["public_phone"][1] == "+39 02 1234 5678"
    assert table["time_zone"][1] == "Europe/Rome"
    assert table["hours_tuesday"][1] == "19:00–23:30"
    assert table["booking_max_party_size"][1] == "1 person"
    assert table["booking_deposit"][1] == "No deposit"
    assert table["languages"][1] == "Italian (it), English (en)"


def test_japanese_yen_have_no_minor_units() -> None:
    testbed = AssemblyTestbed()
    business = seed_japanese_restaurant(testbed)

    table = as_table(
        BusinessFactsTransformer().transform(build_source(testbed, business))
    )

    assert table["menu_item_1"] == ("Menu item: にぎり盛り合わせ", "Price: 1500 JPY")
    assert table["booking_deposit"] == ("Deposit", "1000 JPY")
    assert table["address"][1] == "東京都中央区銀座1-2-3"
    assert table["languages"][1] == "Japanese (ja), English (en)"
    assert "public_phone" not in table
    assert "city" in table


def test_israeli_clinic_keeps_right_to_left_texts_untouched() -> None:
    testbed = AssemblyTestbed()
    business = seed_israeli_clinic(testbed)

    table = as_table(
        BusinessFactsTransformer().transform(build_source(testbed, business))
    )

    assert table["business_name"][1] == "מרפאת השרון"
    assert table["address"][1] == "רחוב דיזנגוף 50, תל אביב"
    assert table["service_1"] == (
        "Service: ייעוץ רופא",
        "Price: 300.00 ILS; Duration: 30 minutes",
    )
    assert table["resource_1"] == (
        "Bookable staff member: ד״ר כהן",
        "Up to 1 person; Booked in slots of 30 minutes",
    )
    assert table["public_phone"][1] == "+972 3-123-4567"
    assert table["hours_sunday"][1] == "08:00–16:00"
    assert table["languages"][1] == "Hebrew (he), Arabic (ar), English (en)"


def test_item_without_details_and_item_in_its_own_currency() -> None:
    testbed = AssemblyTestbed()
    business = seed_online_shop(testbed)
    testbed.knowledge_repo.save(
        build_menu_item(business, "Gift card", None, kind=KnowledgeItemKind.PRODUCT)
    )
    testbed.knowledge_repo.save(
        build_menu_item(
            business,
            "Imported grinder",
            12900,
            kind=KnowledgeItemKind.PRODUCT,
            currency_code="EUR",
        )
    )

    table = as_table(
        BusinessFactsTransformer().transform(build_source(testbed, business))
    )

    assert table["product_2"] == ("Product: Gift card", "No details")
    assert table["product_3"] == ("Product: Imported grinder", "Price: 129.00 EUR")
