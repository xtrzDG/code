"""English fact-table descriptions of profile, knowledge and resource records."""

from app.schemas.constants.bookings import BookingUnit, ResourceKind
from app.schemas.constants.businesses import BusinessLinkKind
from app.schemas.constants.knowledge import KnowledgeItemKind
from app.schemas.constants.niches import QuestionAnswerType
from app.schemas.domain.knowledge import KnowledgeItemDocument
from app.schemas.domain.profiles import BookingRules
from app.schemas.domain.resources import ResourceDocument, ScheduleExceptionDocument
from app.schemas.dto.niches import QuestionDefinition
from app.schemas.typings.localization.constrained_strings import CurrencyCode
from app.utilities.assembly.fact_formatting import (
    format_compact_weekly_hours,
    format_minutes,
    format_money_amount,
    format_opening_intervals,
    format_people,
    format_phone_number_text,
    read_english_text,
)

CHOICE_SEPARATOR: str = ","
KNOWLEDGE_KIND_LABELS: dict[KnowledgeItemKind, str] = {
    KnowledgeItemKind.FAQ: "Question",
    KnowledgeItemKind.POLICY: "Policy",
    KnowledgeItemKind.MENU_ITEM: "Menu item",
    KnowledgeItemKind.SERVICE: "Service",
    KnowledgeItemKind.ROOM_TYPE: "Room type",
    KnowledgeItemKind.PACKAGE: "Package",
    KnowledgeItemKind.VEHICLE: "Vehicle",
    KnowledgeItemKind.PRODUCT: "Product",
}
RESOURCE_KIND_NOUNS: dict[ResourceKind, str] = {
    ResourceKind.TABLE: "table",
    ResourceKind.ROOM: "room",
    ResourceKind.STAFF: "staff member",
    ResourceKind.ARENA: "arena",
    ResourceKind.BAY: "service bay",
    ResourceKind.VEHICLE: "vehicle",
    ResourceKind.SLOT: "time slot",
}
LINK_LABELS: dict[BusinessLinkKind, str] = {
    BusinessLinkKind.MENU: "Menu link",
    BusinessLinkKind.MAP: "Map link",
    BusinessLinkKind.PAYMENT: "Payment link",
    BusinessLinkKind.BOOKING_PAGE: "Online booking page",
    BusinessLinkKind.DELIVERY: "Delivery link",
    BusinessLinkKind.WEBSITE: "Website",
    BusinessLinkKind.PRIVACY: "Privacy notice",
}


def describe_schedule_exception(exception: ScheduleExceptionDocument) -> str:
    """ "Closed all day — Christmas" or "Open 10:00–16:00 — Christmas"."""

    state: str
    if exception.is_closed_all_day:
        state = "Closed all day"
    elif exception.special_hours:
        state = f"Open {format_opening_intervals(exception.special_hours)}"
    else:
        state = "Special opening hours"

    if exception.note is None or exception.note.strip() == "":
        return state

    return f"{state} — {exception.note.strip()}"


def humanize_niche_answer(question: QuestionDefinition, answer_text: str) -> str:
    """
    Choice keys become their English labels ("yes" -> "Yes", "kids,vegan"
    -> "Kids menu, Vegan dishes"); phone numbers get international format.
    """

    if question.answer_type is QuestionAnswerType.PHONE_NUMBER:
        return format_phone_number_text(answer_text.strip())

    if not question.choices:
        return answer_text.strip()

    choice_labels: dict[str, str] = {
        str(choice.key): read_english_text(choice.labels) for choice in question.choices
    }
    choice_keys: list[str] = [
        part.strip() for part in answer_text.split(CHOICE_SEPARATOR) if part.strip()
    ]
    if not choice_keys or any(key not in choice_labels for key in choice_keys):
        return answer_text.strip()

    return ", ".join(choice_labels[key] for key in choice_keys)


def describe_knowledge_item(
    item: KnowledgeItemDocument,
    business_currency_code: CurrencyCode,
) -> str:
    """
    Body, price, duration, tags and attributes of an item, in that order.
    Prices without their own currency are in the business currency.
    """

    parts: list[str] = []
    if item.body is not None and item.body.strip() != "":
        parts.append(item.body.strip())

    if item.price_minor is not None:
        currency_code: CurrencyCode = item.currency_code or business_currency_code
        parts.append(f"Price: {format_money_amount(item.price_minor, currency_code)}")

    if item.duration_minutes is not None:
        parts.append(f"Duration: {format_minutes(int(item.duration_minutes))}")

    if item.tags:
        parts.append("Tags: " + ", ".join(str(tag) for tag in item.tags))

    parts.extend(
        f"{attribute.key.replace('_', ' ')}: {attribute.value.strip()}"
        for attribute in item.attributes
        if attribute.value.strip() != ""
    )
    if not parts:
        return "No details"

    return "; ".join(parts)


def describe_resource(
    resource: ResourceDocument,
    booking_rules: BookingRules | None,
) -> str:
    """Capacity, units, booking unit or slot length, and own hours of a resource."""

    parts: list[str] = [f"Up to {format_people(int(resource.capacity))}"]
    if int(resource.unit_count) > 1:
        parts.append(f"{int(resource.unit_count)} identical units")

    if resource.booking_unit is BookingUnit.NIGHT:
        parts.append("Booked per night")
    else:
        slot_minutes: int | None = (
            int(resource.slot_minutes)
            if resource.slot_minutes is not None
            else (
                int(booking_rules.slot_minutes) if booking_rules is not None else None
            )
        )
        parts.append(
            f"Booked in slots of {format_minutes(slot_minutes)}"
            if slot_minutes is not None
            else "Booked by time slot"
        )

    if resource.schedule:
        parts.append(f"Own hours: {format_compact_weekly_hours(resource.schedule)}")

    return "; ".join(parts)


def describe_booking_rule_rows(
    rules: BookingRules,
    business_currency_code: CurrencyCode,
) -> list[tuple[str, str, str]]:
    """(key, label, value) rows of the booking rules, in a fixed order."""

    rows: list[tuple[str, str, str]] = [
        ("booking_unit", "What is booked", RESOURCE_KIND_NOUNS[rules.resource_kind]),
        (
            "booking_length",
            "Default booking length",
            format_minutes(int(rules.slot_minutes)),
        ),
        (
            "booking_max_party_size",
            "Maximum party size",
            format_people(int(rules.max_party_size)),
        ),
        (
            "booking_min_notice",
            "Minimum notice before a booking",
            (
                format_minutes(int(rules.min_notice_minutes))
                if int(rules.min_notice_minutes) > 0
                else "No minimum notice"
            ),
        ),
        (
            "booking_deposit",
            "Deposit",
            (
                format_money_amount(
                    rules.deposit_minor,
                    rules.deposit_currency_code or business_currency_code,
                )
                if rules.deposit_minor is not None and int(rules.deposit_minor) > 0
                else "No deposit"
            ),
        ),
    ]
    if rules.cancellation_policy is not None:
        rows.append(
            ("booking_cancellation", "Cancellation policy", rules.cancellation_policy)
        )

    return rows
