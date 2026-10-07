"""The changes between the live fact table and today's, one kind at a time."""

from app.schemas.constants.businesses import BusinessLinkKind, Weekday
from app.schemas.constants.knowledge import KnowledgeItemKind
from app.schemas.constants.setup import (
    PendingChangeAction,
    PendingChangeArea,
    PendingChangeDetail,
    PendingChangeField,
)
from app.schemas.domain.assistants import BusinessFact
from app.schemas.dto.setup.pending_changes import PendingChange
from app.schemas.typings.bookings.constrained_strings import LocalDate
from app.schemas.typings.profiles.constrained_strings import FactKey
from app.schemas.typings.profiles.strings import FactLabel, FactValue
from app.utilities.assembly.fact_diff import diff_fact_tables, read_price

TODAY = LocalDate("2026-10-03")


def fact(key: str, label: str, value: str) -> BusinessFact:
    return BusinessFact(
        key=FactKey(key), label=FactLabel(label), value=FactValue(value)
    )


def diff(
    live: list[BusinessFact],
    current: list[BusinessFact],
    answer_labels: dict[str, str] | None = None,
) -> list[PendingChange]:
    return diff_fact_tables(live, current, TODAY, answer_labels or {})


KHACHAPURI = fact(
    "menu_item_1", "Menu item: Khachapuri", "Cheese bread; Price: 18.00 GEL"
)


def test_the_same_table_has_no_changes() -> None:
    assert diff([KHACHAPURI], [KHACHAPURI]) == []


def test_a_new_price_is_named_with_both_prices() -> None:
    raised = fact(
        "menu_item_1", "Menu item: Khachapuri", "Cheese bread; Price: 20.00 GEL"
    )

    [change] = diff([KHACHAPURI], [raised])

    assert change.area is PendingChangeArea.OFFER
    assert change.action is PendingChangeAction.CHANGED
    assert change.item_kind is KnowledgeItemKind.MENU_ITEM
    assert str(change.subject) == "Khachapuri"
    assert change.detail is PendingChangeDetail.PRICE
    assert (str(change.before), str(change.after)) == ("18.00 GEL", "20.00 GEL")


def test_other_edits_of_an_item_are_its_details() -> None:
    reworded = fact(
        "menu_item_1", "Menu item: Khachapuri", "Cheese boat; Price: 18.00 GEL"
    )

    [change] = diff([KHACHAPURI], [reworded])

    assert change.detail is PendingChangeDetail.DETAILS
    assert change.before is None and change.after is None


def test_a_new_item_does_not_turn_the_ones_after_it_into_changes() -> None:
    lobio = fact("menu_item_1", "Menu item: Lobio", "Bean stew; Price: 12.00 GEL")
    moved = fact(
        "menu_item_2", "Menu item: Khachapuri", "Cheese bread; Price: 18.00 GEL"
    )

    changes = diff([KHACHAPURI], [lobio, moved])

    assert [(c.action, str(c.subject)) for c in changes] == [
        (PendingChangeAction.ADDED, "Lobio")
    ]


def test_removed_items_questions_and_resources_are_named() -> None:
    faq = fact("faq_1", "Frequently asked question: Parking?", "Yes, behind the house")
    table = fact("resource_1", "Bookable table: Terrace", "4 seats")

    changes = diff([KHACHAPURI, faq, table], [])

    assert [(c.area, c.action, str(c.subject)) for c in changes] == [
        (PendingChangeArea.OFFER, PendingChangeAction.REMOVED, "Khachapuri"),
        (PendingChangeArea.QUESTIONS, PendingChangeAction.REMOVED, "Parking?"),
        (PendingChangeArea.RESOURCES, PendingChangeAction.REMOVED, "Terrace"),
    ]


def test_profile_hours_links_rules_and_languages_by_their_key() -> None:
    live = [
        fact("address", "Address", "Rustaveli 1"),
        fact("hours_monday", "Opening hours on Monday", "10:00-22:00"),
        fact("booking_deposit", "Deposit", "none"),
        fact("default_language", "Main language", "ka"),
    ]
    current = [
        fact("address", "Address", "Rustaveli 2"),
        fact("hours_monday", "Opening hours on Monday", "12:00-22:00"),
        fact("booking_deposit", "Deposit", "none"),
        fact("default_language", "Main language", "ru"),
        fact("link_menu", "Menu", "https://example.com/menu"),
    ]

    changes = diff(live, current)

    assert [(c.area, c.action) for c in changes] == [
        (PendingChangeArea.PROFILE, PendingChangeAction.CHANGED),
        (PendingChangeArea.HOURS, PendingChangeAction.CHANGED),
        (PendingChangeArea.LINKS, PendingChangeAction.ADDED),
        (PendingChangeArea.LANGUAGES, PendingChangeAction.CHANGED),
    ]
    assert changes[0].field is PendingChangeField.ADDRESS
    assert changes[1].weekday is Weekday.MONDAY
    assert changes[2].link_kind is BusinessLinkKind.MENU
    assert changes[3].field is PendingChangeField.DEFAULT_LANGUAGE


def test_booking_rules_are_their_own_area() -> None:
    [change] = diff([], [fact("booking_deposit", "Deposit", "20 GEL")])

    assert change.area is PendingChangeArea.BOOKING_RULES
    assert change.field is PendingChangeField.BOOKING_DEPOSIT


def test_special_days_come_with_their_date_and_passed_ones_are_not_changes() -> None:
    passed = fact("special_day_1", "Special day 2026-09-01", "Closed")
    coming = fact("special_day_1", "Special day 2026-12-31", "Closed")

    changes = diff([passed], [coming])

    assert [(c.area, c.action, str(c.date)) for c in changes] == [
        (PendingChangeArea.SPECIAL_DAYS, PendingChangeAction.ADDED, "2026-12-31")
    ]


def test_niche_answers_are_named_by_the_question_in_the_owners_language() -> None:
    live = [fact("delivery", "Do you deliver?", "No")]
    current = [fact("delivery", "Do you deliver?", "Yes, within 3 km")]

    [labelled] = diff(live, current, {"delivery": "Есть ли доставка?"})
    [plain] = diff(live, current)

    assert labelled.area is PendingChangeArea.ANSWERS
    assert str(labelled.subject) == "Есть ли доставка?"
    assert str(plain.subject) == "Do you deliver?"


def test_the_price_is_the_last_price_part_of_a_description() -> None:
    assert read_price("Spicy; Price: 9.00 GEL") == "9.00 GEL"
    assert read_price("Price: list; Price: 9.00 GEL") == "9.00 GEL"
    assert read_price("No price here") is None
