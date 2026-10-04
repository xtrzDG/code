"""
Tool results as the language model reads them.

Results are compact JSON objects with plain values: prices in major units
of their currency next to the formatted price, dates and times in the
business time zone. Errors are `{"error": "..."}` with a message the model
can act on (ask again, choose another date, pass to a colleague).
Availability and booking results and their errors also state
`business_today`, so relative dates are checked against today.
"""

from pydantic import ValidationError

from app.schemas.dto.billing import Money
from app.schemas.dto.bookings import AvailabilityResult, BookingResult, LeadView
from app.schemas.dto.handoffs import HandoffResult, UnansweredQuestionView
from app.schemas.dto.knowledge import (
    KnowledgeItemView,
    KnowledgeSearchResult,
    PriceLookupResult,
    SendLinkResult,
)
from app.schemas.typings.conversations.strings import LlmToolResultJson
from app.utilities.conversations.llm_transcript import encode_json
from app.utilities.conversations.offer_payloads import (
    major_units,
    render_offer,
    render_seasons,
    render_stay_quote,
)
from app.utilities.conversations.untrusted_text import wrap_untrusted
from app.utilities.money.money_math import (
    convert_money_to_major_units,
    get_currency_minor_unit_digits,
)

MAX_REPORTED_INPUT_ERRORS: int = 3
MAX_ERROR_MESSAGE_LENGTH: int = 300


def render_knowledge_search(result: KnowledgeSearchResult) -> LlmToolResultJson:
    return render({"items": [render_knowledge_item(item) for item in result.items]})


def render_price_lookup(result: PriceLookupResult) -> LlmToolResultJson:
    if not result.matches:
        return render(
            {
                "found": False,
                "note": "Not in the price list: do not name any price.",
                "matches": [],
            }
        )

    payload: dict[str, object] = {
        "found": True,
        "matches": [render_knowledge_item(item) for item in result.matches],
    }
    if result.stay_quotes:
        payload["stay_quotes"] = [
            render_stay_quote(quote) for quote in result.stay_quotes
        ]

    return render(payload)


def render_knowledge_item(item: KnowledgeItemView) -> dict[str, object]:
    rendered: dict[str, object] = {
        "id": str(item.id),
        "kind": item.kind.value,
        "title": str(item.title),
    }
    if item.body is not None:
        body: str = str(item.body)
        rendered["body"] = wrap_untrusted(body) if item.is_imported else body

    if item.price_minor is not None and item.currency_code is not None:
        rendered["price"] = format_major_units(
            Money(amount_minor=item.price_minor, currency_code=item.currency_code)
        )
        rendered["currency"] = str(item.currency_code)
        if item.formatted_price is not None:
            rendered["price_text"] = str(item.formatted_price)

    if item.duration_minutes is not None:
        rendered["duration_minutes"] = int(item.duration_minutes)

    if item.seasonal_rates and item.currency_code is not None:
        rendered["seasonal_nightly_rates"] = render_seasons(
            item.seasonal_rates, item.currency_code
        )

    if item.tags:
        rendered["tags"] = [str(tag) for tag in item.tags]

    return rendered


def render_availability(
    result: AvailabilityResult,
    business_today: str | None = None,
) -> LlmToolResultJson:
    slots: list[dict[str, object]] = []
    for slot in result.slots:
        rendered_slot: dict[str, object] = {
            "resource_id": str(slot.resource_id),
            "resource_name": str(slot.resource_name),
            "unit": slot.booking_unit.value,
            "date": str(slot.date),
        }
        if slot.time is not None:
            rendered_slot["time"] = str(slot.time)

        if slot.duration_minutes is not None:
            rendered_slot["duration_minutes"] = int(slot.duration_minutes)

        if slot.nights is not None:
            rendered_slot["nights"] = int(slot.nights)

        if slot.stay_quote is not None:
            rendered_slot["stay_price"] = render_stay_quote(slot.stay_quote)

        slots.append(rendered_slot)

    payload: dict[str, object] = {
        "timezone": str(result.timezone),
        "is_open_on_date": result.is_open_on_date,
        "slots": slots,
    }
    if result.service is not None:
        payload["service"] = render_offer(result.service)

    if result.services:
        payload["bookable_services"] = [
            render_offer(offer) for offer in result.services
        ]

    return render(with_business_today(payload, business_today))


def render_booking(
    result: BookingResult,
    business_today: str | None = None,
) -> LlmToolResultJson:
    booking = result.booking
    rendered: dict[str, object] = {
        "booking_id": str(booking.id),
        "status": booking.status.value,
        "resource_name": str(booking.resource_name),
        "date": str(booking.date),
        "end_date": str(booking.end_date),
        "party_size": int(booking.party_size),
        "timezone": str(booking.timezone),
        "confirmation_text": str(result.confirmation_text),
    }
    if booking.time is not None:
        rendered["time"] = str(booking.time)

    if booking.end_time is not None:
        rendered["end_time"] = str(booking.end_time)

    if booking.contact_name is not None:
        rendered["name"] = wrap_untrusted(str(booking.contact_name))

    if booking.contact_phone_number is not None:
        rendered["phone"] = str(booking.contact_phone_number)

    if booking.service_title is not None:
        rendered["service"] = str(booking.service_title)

    if booking.value_minor is not None and booking.currency_code is not None:
        rendered["price"] = major_units(int(booking.value_minor), booking.currency_code)
        rendered["currency"] = str(booking.currency_code)

    return render(with_business_today(rendered, business_today))


def render_lead(lead: LeadView) -> LlmToolResultJson:
    return render(
        {
            "lead_id": str(lead.id),
            "lead_type": lead.lead_type.value,
            "status": lead.status.value,
        }
    )


def render_handoff(result: HandoffResult) -> LlmToolResultJson:
    return render(
        {
            "handoff_id": str(result.id),
            "status": result.status.value,
            "customer_message": str(result.customer_message),
        }
    )


def render_link(result: SendLinkResult) -> LlmToolResultJson:
    if result.url is None:
        return render(
            {
                "kind": result.kind.value,
                "url": None,
                "note": "The business has no such link: do not invent one.",
            }
        )

    return render({"kind": result.kind.value, "url": str(result.url)})


def render_phone_link(
    result: SendLinkResult, can_text_caller: bool
) -> LlmToolResultJson:
    """
    send_link on the phone: never the address itself (nobody can type it
    while listening). Whether the platform texts it right after the call
    decides what the agent may promise.
    """

    if result.url is None:
        return render_link(result)

    if can_text_caller:
        return render(
            {
                "kind": result.kind.value,
                "texted_after_call": True,
                "note": 'Say "I will text you the link"; it is sent by message '
                "right after the call. Never read it aloud.",
            }
        )

    return render(
        {
            "kind": result.kind.value,
            "texted_after_call": False,
            "note": "This caller cannot get a message from the business: do not "
            "promise one and never read the link aloud. Say where to find it "
            "or offer to pass the request to a colleague.",
        }
    )


def render_unanswered_question(question: UnansweredQuestionView) -> LlmToolResultJson:
    return render({"recorded": True, "question_id": str(question.id)})


def render_tool_error(
    message: str,
    business_today: str | None = None,
) -> LlmToolResultJson:
    """An error result; the message is shortened so it never floods the model."""

    return render(
        with_business_today(
            {"error": message[:MAX_ERROR_MESSAGE_LENGTH]}, business_today
        )
    )


def with_business_today(
    payload: dict[str, object],
    business_today: str | None,
) -> dict[str, object]:
    """The payload with today at the business ("2026-10-01 (Thursday)") when known."""

    if business_today is None:
        return payload

    return {**payload, "business_today": business_today}


def describe_tool_input_error(error: ValidationError) -> str:
    """Which arguments were wrong and why, without repeating their values."""

    problems: list[str] = []
    for detail in error.errors()[:MAX_REPORTED_INPUT_ERRORS]:
        location: str = ".".join(str(part) for part in detail["loc"]) or "input"
        problems.append(f"{location}: {detail['msg']}")

    return "Invalid tool input: " + "; ".join(problems)


def format_major_units(money: Money) -> str:
    """51700 GEL minor units -> "517.00" (the currency's own precision)."""

    digits: int = int(get_currency_minor_unit_digits(money.currency_code))
    return f"{convert_money_to_major_units(money):.{digits}f}"


def render(payload: dict[str, object]) -> LlmToolResultJson:
    return LlmToolResultJson(encode_json(payload))
