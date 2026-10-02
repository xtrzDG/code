"""
Business facts of a full profile: order, inactive records, labels, days, resources.
"""

from app.schemas.typings.bookings.constrained_strings import LocalDate
from app.transformers.assembly.business_facts_transformer import (
    BusinessFactsTransformer,
)
from tests.assembly.business_facts_helpers import as_table, build_source
from tests.assembly.georgian_restaurant_seed import seed_georgian_restaurant
from tests.assembly.testbed import AssemblyTestbed


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
