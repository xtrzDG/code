"""
Tool calls of demo conversations with the arguments and results the real
tools take and give (see app/utilities/conversations/tool_payloads.py), so
the conversation card shows what an owner would see.
"""

from collections.abc import Sequence

from typed_time_provider import Microseconds

from app.registries.demo.demo_clock import DemoClock
from app.registries.demo.demo_lines import tool
from app.schemas.constants.assistants import AssistantToolName
from app.schemas.constants.bookings import LeadType
from app.schemas.constants.businesses import BusinessLinkKind
from app.schemas.constants.handoffs import HandoffReason, HandoffUrgency
from app.schemas.domain.conversations import ToolCallRecord
from app.schemas.domain.knowledge import KnowledgeItemDocument
from app.schemas.domain.resources import ResourceDocument
from app.schemas.dto.billing import Money
from app.schemas.typings.bookings.prefixed_id import BookingId, LeadId
from app.schemas.typings.handoffs.prefixed_id import HandoffId, UnansweredQuestionId
from app.utilities.conversations.tool_payloads import format_major_units


def availability(
    clock: DemoClock,
    resource: ResourceDocument,
    moment: Microseconds,
    party_size: int,
    minutes: int = 120,
) -> ToolCallRecord:
    date: str = str(clock.local_date_of(moment))
    time: str = clock.clock_of(moment)
    return tool(
        AssistantToolName.CHECK_AVAILABILITY,
        {"date": date, "time": time, "party_size": party_size},
        {
            "timezone": str(clock.timezone),
            "is_open_on_date": True,
            "slots": [
                {
                    "resource_id": str(resource.id),
                    "resource_name": str(resource.name),
                    "unit": resource.booking_unit.value,
                    "date": date,
                    "time": time,
                    "duration_minutes": minutes,
                }
            ],
        },
    )


def booking(
    clock: DemoClock,
    booking_id: BookingId,
    resource: ResourceDocument,
    moment: Microseconds,
    party_size: int,
    name: str,
    phone: str | None,
    confirmation: str,
    status: str = "confirmed",
    minutes: int = 120,
) -> ToolCallRecord:
    date: str = str(clock.local_date_of(moment))
    end: Microseconds = clock.later(moment, minutes)
    arguments: dict[str, object] = {
        "name": name,
        "date": date,
        "time": clock.clock_of(moment),
        "party_size": party_size,
    }
    result: dict[str, object] = {
        "booking_id": str(booking_id),
        "status": status,
        "resource_name": str(resource.name),
        "date": date,
        "end_date": str(clock.local_date_of(end)),
        "party_size": party_size,
        "timezone": str(clock.timezone),
        "confirmation_text": confirmation,
        "time": clock.clock_of(moment),
        "end_time": clock.clock_of(end),
        "name": name,
    }
    if phone is not None:
        arguments["phone"] = phone
        result["phone"] = phone

    return tool(AssistantToolName.CREATE_BOOKING, arguments, result)


def cancellation(
    clock: DemoClock,
    booking_id: BookingId,
    resource: ResourceDocument,
    moment: Microseconds,
    party_size: int,
    confirmation: str,
) -> ToolCallRecord:
    date: str = str(clock.local_date_of(moment))
    return tool(
        AssistantToolName.CANCEL_BOOKING,
        {"booking_id": str(booking_id)},
        {
            "booking_id": str(booking_id),
            "status": "cancelled",
            "resource_name": str(resource.name),
            "date": date,
            "time": clock.clock_of(moment),
            "party_size": party_size,
            "timezone": str(clock.timezone),
            "confirmation_text": confirmation,
        },
    )


def price(query: str, *items: KnowledgeItemDocument) -> ToolCallRecord:
    return tool(
        AssistantToolName.GET_PRICE,
        {"item_name": query},
        {"found": True, "matches": [describe_item(item) for item in items]}
        if items
        else {
            "found": False,
            "note": "Not in the price list: do not name any price.",
            "matches": [],
        },
    )


def search(
    query: str, items: Sequence[KnowledgeItemDocument], language: str | None = None
) -> ToolCallRecord:
    arguments: dict[str, object] = {"query": query}
    if language is not None:
        arguments["language"] = language

    return tool(
        AssistantToolName.SEARCH_KNOWLEDGE,
        arguments,
        {"items": [describe_item(item) for item in items]},
    )


def lead(
    lead_id: LeadId,
    lead_type: LeadType,
    details: str,
    name: str,
    phone: str | None = None,
    requested_date: str | None = None,
    party_size: int | None = None,
    budget: str | None = None,
) -> ToolCallRecord:
    arguments: dict[str, object] = {
        "lead_type": lead_type.value,
        "details": details,
        "name": name,
    }
    for key, value in (
        ("phone", phone),
        ("requested_date", requested_date),
        ("party_size", party_size),
        ("budget", budget),
    ):
        if value is not None:
            arguments[key] = value

    return tool(
        AssistantToolName.CREATE_LEAD,
        arguments,
        {"lead_id": str(lead_id), "lead_type": lead_type.value, "status": "new"},
    )


def handoff(
    handoff_id: HandoffId,
    reason: HandoffReason,
    summary: str,
    urgency: HandoffUrgency,
) -> ToolCallRecord:
    return tool(
        AssistantToolName.HANDOFF_TO_HUMAN,
        {"reason": reason.value, "summary": summary, "urgency": urgency.value},
        {"handoff_id": str(handoff_id), "status": "notified"},
    )


def link(kind: BusinessLinkKind, url: str) -> ToolCallRecord:
    return tool(
        AssistantToolName.SEND_LINK,
        {"kind": kind.value},
        {"kind": kind.value, "url": url},
    )


def unanswered(question_id: UnansweredQuestionId, question: str) -> ToolCallRecord:
    return tool(
        AssistantToolName.RECORD_UNANSWERED_QUESTION,
        {"question": question},
        {"recorded": True, "question_id": str(question_id)},
    )


def describe_item(item: KnowledgeItemDocument) -> dict[str, object]:
    described: dict[str, object] = {
        "id": str(item.id),
        "kind": item.kind.value,
        "title": str(item.title),
    }
    if item.body is not None:
        described["body"] = str(item.body)

    if item.price_minor is not None and item.currency_code is not None:
        described["price"] = format_major_units(
            Money(amount_minor=item.price_minor, currency_code=item.currency_code)
        )
        described["currency"] = str(item.currency_code)

    if item.duration_minutes is not None:
        described["duration_minutes"] = int(item.duration_minutes)

    return described
