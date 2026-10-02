"""Facts from minimal or reordered inputs, registries, helpers, keys and dates."""

import random

from typed_time_provider import Microseconds

from app.schemas.constants.businesses import Weekday
from app.schemas.constants.niches import NicheKey
from app.schemas.typings.billing.constrained_integers import MoneyAmountMinor
from app.schemas.typings.localization.constrained_strings import (
    CountryCode,
    CurrencyCode,
    LanguageTag,
    TimezoneName,
)
from app.transformers.assembly.business_facts_transformer import (
    BusinessFactsTransformer,
)
from app.utilities.assembly.fact_formatting import (
    compute_local_date,
    format_money_amount,
    format_opening_intervals,
    unique_preserving_order,
)
from app.utilities.assembly.fact_table import build_unique_fact_key
from tests.assembly.builders import interval
from tests.assembly.business_facts_helpers import as_table, build_source
from tests.assembly.georgian_restaurant_seed import seed_georgian_restaurant
from tests.assembly.international_business_seeds import seed_online_shop
from tests.assembly.testbed import AssemblyTestbed


def test_minimal_profile_gives_only_known_facts() -> None:
    testbed = AssemblyTestbed()
    business = seed_online_shop(testbed, has_opening_hours=False)

    facts = BusinessFactsTransformer().transform(build_source(testbed, business))

    assert [str(fact.key) for fact in facts] == [
        "business_name",
        "business_type",
        "country",
        "time_zone",
        "product_1",
        "languages",
        "default_language",
    ]
    assert as_table(facts)["product_1"] == (
        "Product: Espresso beans 1 kg",
        "Price: 24.50 USD",
    )


def test_facts_do_not_depend_on_input_order() -> None:
    testbed = AssemblyTestbed()
    business = seed_georgian_restaurant(testbed)
    source = build_source(testbed, business)
    shuffled_items = list(source.knowledge_items)
    shuffled_resources = list(source.resources)
    shuffled_exceptions = list(source.schedule_exceptions)
    shuffled_hours = list(source.profile.hours)
    for values in (
        shuffled_items,
        shuffled_resources,
        shuffled_exceptions,
        shuffled_hours,
    ):
        random.Random(7).shuffle(values)

    shuffled_profile = source.profile.model_copy(deep=True)
    shuffled_profile.hours = shuffled_hours
    shuffled_source = source.model_copy(
        update={
            "knowledge_items": shuffled_items,
            "resources": shuffled_resources,
            "schedule_exceptions": shuffled_exceptions,
            "profile": shuffled_profile,
        }
    )

    assert BusinessFactsTransformer().transform(
        shuffled_source
    ) == BusinessFactsTransformer().transform(source)


def test_language_unknown_to_the_registry_is_named_by_its_tag() -> None:
    testbed = AssemblyTestbed()
    business = seed_online_shop(testbed)
    source = build_source(testbed, business)
    multilingual_business = business.model_copy(deep=True)
    multilingual_business.languages = [LanguageTag("en"), LanguageTag("sw")]

    table = as_table(
        BusinessFactsTransformer().transform(
            source.model_copy(update={"business": multilingual_business})
        )
    )

    assert table["languages"][1] == "English (en), sw"


def test_formatting_helpers() -> None:
    assert format_opening_intervals(
        [
            interval(Weekday.MONDAY, "14:00", "18:00"),
            interval(Weekday.MONDAY, "09:00", "13:00"),
        ]
    ) == ("09:00–13:00, 14:00–18:00")
    assert format_money_amount(MoneyAmountMinor(0), CurrencyCode("GEL")) == "0.00 GEL"
    assert format_money_amount(MoneyAmountMinor(1250), CurrencyCode("KWD")) == (
        "1.250 KWD"
    )
    assert (
        format_money_amount(MoneyAmountMinor(150_000_000), CurrencyCode("EUR"))
        == "1500000.00 EUR"
    )
    assert unique_preserving_order(["A", " a ", "", "b", "B "]) == ["A", "b"]


def test_fact_keys_stay_unique_and_valid() -> None:
    used_keys: set[str] = set()

    assert build_unique_fact_key("menu_item_1", used_keys) == "menu_item_1"
    assert build_unique_fact_key("menu_item_1", used_keys) == "menu_item_1_2"
    assert build_unique_fact_key("menu_item_1", used_keys) == "menu_item_1_3"
    long_key = build_unique_fact_key("x" * 80, used_keys)
    assert len(long_key) <= 64


def test_local_date_follows_the_business_time_zone() -> None:
    # 2026-09-30 22:30 UTC is already 1 October in Tbilisi (UTC+4) and Tokyo,
    # but still 30 September in New York.
    moment = Microseconds(1_790_807_400 * 1_000_000)

    assert compute_local_date(moment, TimezoneName("Asia/Tbilisi")) == "2026-10-01"
    assert compute_local_date(moment, TimezoneName("Asia/Tokyo")) == "2026-10-01"
    assert compute_local_date(moment, TimezoneName("America/New_York")) == (
        "2026-09-30"
    )


def test_country_and_niche_come_from_the_registries() -> None:
    testbed = AssemblyTestbed()
    business = seed_georgian_restaurant(testbed)
    source = build_source(testbed, business).model_copy(
        update={
            "country": testbed.country_registry.get(CountryCode("IT")),
            "niche": testbed.niche_registry.get(NicheKey.CLINIC),
        }
    )

    table = as_table(BusinessFactsTransformer().transform(source))

    assert table["country"][1] == "Italy"
    assert table["business_type"][1] == "Clinics and dentists"
    assert "live_music" not in table
