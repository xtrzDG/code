import random

from typed_time_provider import Microseconds

from app.schemas.constants.businesses import Weekday
from app.schemas.constants.knowledge import KnowledgeItemKind
from app.schemas.constants.niches import NicheKey
from app.schemas.domain.assistants import BusinessFact
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.domain.profiles import BusinessProfileDocument
from app.schemas.dto.assistants.assembly_sources import BusinessFactsSource
from app.schemas.typings.billing.constrained_integers import MoneyAmountMinor
from app.schemas.typings.bookings.constrained_strings import LocalDate
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
from tests.assembly.builders import build_menu_item, interval
from tests.assembly.georgian_restaurant_seed import seed_georgian_restaurant
from tests.assembly.international_business_seeds import (
    seed_israeli_clinic,
    seed_italian_restaurant,
    seed_japanese_restaurant,
    seed_online_shop,
)
from tests.assembly.testbed import AssemblyTestbed

TODAY: LocalDate = LocalDate("2026-10-01")


def build_source(
    testbed: AssemblyTestbed,
    business: BusinessDocument,
    today: LocalDate = TODAY,
) -> BusinessFactsSource:
    profile: BusinessProfileDocument | None = testbed.profile_repo.get_by_business(
        business.id
    )
    assert profile is not None
    return BusinessFactsSource(
        business=business,
        profile=profile,
        niche=testbed.niche_registry.get(business.niche_key),
        country=testbed.country_registry.get(business.country_code),
        language_profiles=[
            testbed.language_registry.get(language) for language in business.languages
        ],
        knowledge_items=testbed.knowledge_repo.list_by_business(business.id),
        resources=testbed.resource_repo.list_by_business(business.id),
        schedule_exceptions=testbed.exception_repo.list_by_business(business.id),
        today=today,
    )


def as_table(facts: list[BusinessFact]) -> dict[str, tuple[str, str]]:
    return {str(fact.key): (str(fact.label), str(fact.value)) for fact in facts}


def test_georgian_restaurant_facts_are_complete_and_ordered() -> None:
    testbed = AssemblyTestbed()
    business = seed_georgian_restaurant(testbed)

    facts = BusinessFactsTransformer().transform(build_source(testbed, business))

    assert [str(fact.key) for fact in facts] == [
        "business_name",
        "business_type",
        "city",
        "country",
        "address",
        "maps_link",
        "public_phone",
        "time_zone",
        "hours_monday",
        "hours_tuesday",
        "hours_wednesday",
        "hours_thursday",
        "hours_friday",
        "hours_saturday",
        "hours_sunday",
        "special_day_1",
        "special_day_2",
        "special_day_3",
        "live_music",
        "cuisine",
        "banquet_phone",
        "faq_1",
        "menu_item_1",
        "menu_item_2",
        "resource_1",
        "resource_2",
        "booking_unit",
        "booking_length",
        "booking_max_party_size",
        "booking_min_notice",
        "booking_deposit",
        "booking_cancellation",
        "link_menu",
        "link_booking_page",
        "languages",
        "default_language",
    ]
    table = as_table(facts)
    assert table["business_name"] == ("Business name", "Café Rustaveli")
    assert table["business_type"] == ("Type of business", "Restaurants and cafes")
    assert table["public_phone"] == ("Public phone number", "+995 32 212 34 56")
    assert table["time_zone"] == ("Time zone", "Asia/Tbilisi")
    assert table["hours_friday"] == (
        "Opening hours on Friday",
        "12:00–15:00, 18:00–24:00",
    )
    assert table["hours_sunday"] == ("Opening hours on Sunday", "Closed")
    assert table["menu_item_1"] == (
        "Menu item: Khachapuri Adjaruli",
        "Boat-shaped bread with cheese and egg; Price: 18.00 GEL; "
        "Tags: vegetarian; portion size: 400 g",
    )
    assert table["menu_item_2"] == ("Menu item: Mtsvadi", "Price: 24.00 GEL")
    assert table["faq_1"] == (
        "Question: Is there parking?",
        "Yes, free, in the yard",
    )
    assert table["booking_deposit"] == ("Deposit", "50.00 GEL")
    assert table["booking_max_party_size"] == ("Maximum party size", "12 people")
    assert table["booking_min_notice"] == (
        "Minimum notice before a booking",
        "60 minutes",
    )
    assert table["booking_cancellation"] == (
        "Cancellation policy",
        "Free up to 2 hours before",
    )
    assert table["languages"] == (
        "Languages the business serves",
        "Georgian (ka), Russian (ru), English (en)",
    )
    assert table["default_language"] == ("Default language", "Georgian (ka)")
    assert table["link_menu"] == ("Menu link", "https://example.ge/menu")


def test_inactive_records_are_left_out() -> None:
    testbed = AssemblyTestbed()
    business = seed_georgian_restaurant(testbed)

    facts = BusinessFactsTransformer().transform(build_source(testbed, business))
    rendered: str = "\n".join(f"{fact.label}: {fact.value}" for fact in facts)

    assert "Old dish" not in rendered
    assert "Broken table" not in rendered
    assert "2026-11-02" not in rendered


def test_niche_answers_use_english_labels_and_choice_labels() -> None:
    testbed = AssemblyTestbed()
    business = seed_georgian_restaurant(testbed)

    table = as_table(
        BusinessFactsTransformer().transform(build_source(testbed, business))
    )

    assert table["live_music"] == ("Is there live music?", "Yes")
    assert table["cuisine"] == ("Cuisine", "Georgian, European")
    assert table["banquet_phone"] == ("Banquet manager phone", "+995 555 12 34 56")
    assert "kids_menu" not in table
    assert "stale answer" not in str(table)


def test_only_upcoming_special_days_are_listed() -> None:
    testbed = AssemblyTestbed()
    business = seed_georgian_restaurant(testbed)

    table = as_table(
        BusinessFactsTransformer().transform(build_source(testbed, business))
    )
    later_table = as_table(
        BusinessFactsTransformer().transform(
            build_source(testbed, business, LocalDate("2026-12-31"))
        )
    )

    assert table["special_day_1"] == (
        "Special day 2026-11-01",
        "Closed all day (applies to Terrace)",
    )
    assert table["special_day_2"] == (
        "Special day 2026-12-31",
        "Open 12:00–18:00 — New Year's Eve",
    )
    assert table["special_day_3"] == (
        "Special day 2027-01-07",
        "Closed all day — Orthodox Christmas",
    )
    assert "2026-09-01" not in str(table)
    assert later_table["special_day_1"][0] == "Special day 2026-12-31"
    assert "special_day_3" not in later_table


def test_resources_describe_capacity_units_slots_and_own_hours() -> None:
    testbed = AssemblyTestbed()
    business = seed_georgian_restaurant(testbed)

    table = as_table(
        BusinessFactsTransformer().transform(build_source(testbed, business))
    )

    assert table["resource_1"] == (
        "Bookable table: Table 4",
        "Up to 4 people; 3 identical units; Booked in slots of 90 minutes",
    )
    label, value = table["resource_2"]
    assert label == "Bookable table: Terrace"
    assert value.startswith("Up to 8 people; Booked in slots of 120 minutes; ")
    assert "Saturday 12:00–22:00" in value
    assert "Sunday closed" in value


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
