"""
The ten model tools of the concept (section 5) with strict JSON schemas.

Schemas list every property as required and express optional values as
`null`, the shape strict tool use accepts at both OpenAI and Anthropic, and
forbid extra properties. Business, contact, conversation and channel are not
parameters: the server supplies them, so a customer cannot redirect a tool
to another tenant. Formats and ranges are checked by the server-side input
DTOs, which return errors the model can act on.
"""

import json

from app.schemas.constants.assistants import AssistantToolName
from app.schemas.constants.bookings import LeadType, ResourceKind
from app.schemas.constants.businesses import BusinessLinkKind
from app.schemas.constants.handoffs import HandoffReason, HandoffUrgency
from app.schemas.dto.conversations import LlmToolDefinition
from app.schemas.typings.assistants.strings import (
    LlmToolDescription,
    LlmToolInputSchemaJson,
)

type JsonSchema = dict[str, object]

# Reasons the engine sets itself are not offered to the model.
MODEL_HANDOFF_REASONS: tuple[HandoffReason, ...] = tuple(
    reason for reason in HandoffReason if reason is not HandoffReason.UNVERIFIED_NUMBERS
)


def string_property(description: str) -> JsonSchema:
    return {"type": "string", "description": description}


def integer_property(description: str) -> JsonSchema:
    return {"type": "integer", "description": description}


def enum_property(values: list[str], description: str) -> JsonSchema:
    return {"type": "string", "enum": values, "description": description}


def nullable(schema: JsonSchema) -> JsonSchema:
    """The same value or null; the description stays on the outer schema."""

    inner_schema: JsonSchema = {
        key: value for key, value in schema.items() if key != "description"
    }
    return {
        "anyOf": [inner_schema, {"type": "null"}],
        "description": schema["description"],
    }


def object_schema(properties: dict[str, JsonSchema]) -> JsonSchema:
    return {
        "type": "object",
        "properties": properties,
        "required": list(properties),
        "additionalProperties": False,
    }


DATE_HINT: str = "Local date of the business, YYYY-MM-DD."
TIME_HINT: str = "Local time of the business, HH:MM in 24-hour format."
PHONE_HINT: str = (
    "Phone number as the customer gave it, ideally with the country code; "
    "null to use the number the customer contacted us from."
)
RESOURCE_TYPE: JsonSchema = nullable(
    enum_property(
        [kind.value for kind in ResourceKind],
        "What is booked; null for the business's usual resource.",
    )
)

TOOL_SPECIFICATIONS: dict[AssistantToolName, tuple[str, JsonSchema]] = {
    AssistantToolName.SEARCH_KNOWLEDGE: (
        "Search the business knowledge base (menu, services, rooms, packages, "
        "FAQ, policies) when the fact table does not answer the customer. "
        "Returns up to 5 items with ids, prices in the business currency and "
        "durations.",
        object_schema(
            {
                "query": string_property("What to look for, in any language."),
                "language": nullable(
                    string_property(
                        "BCP 47 tag of the query language, e.g. 'ka' or 'pt-BR'; "
                        "null for the conversation language."
                    )
                ),
            }
        ),
    ),
    AssistantToolName.GET_PRICE: (
        "Look up the price of a menu item, service, room or package by name. "
        "Name a price only if it comes from this result or the fact table; "
        "an empty result means the item is not in the price list.",
        object_schema(
            {"item_name": string_property("Name of the item as the customer said.")}
        ),
    ),
    AssistantToolName.CHECK_AVAILABILITY: (
        "Check free time slots (or free nights for stays) on a date in the "
        "business time zone, before offering or creating a booking.",
        object_schema(
            {
                "resource_type": RESOURCE_TYPE,
                "date": string_property(DATE_HINT),
                "time": nullable(string_property(TIME_HINT)),
                "party_size": nullable(integer_property("Number of guests.")),
                "duration_minutes": nullable(
                    integer_property("Length of the visit or service in minutes.")
                ),
                "nights": nullable(integer_property("Number of nights to stay.")),
            }
        ),
    ),
    AssistantToolName.CREATE_BOOKING: (
        "Create a booking. First repeat the date, time, number of guests and "
        "the customer's name and get the customer's confirmation.",
        object_schema(
            {
                "name": string_property("Name the booking is under."),
                "phone": nullable(string_property(PHONE_HINT)),
                "resource_type": RESOURCE_TYPE,
                "date": string_property(DATE_HINT),
                "time": nullable(string_property(TIME_HINT)),
                "party_size": integer_property("Number of guests."),
                "duration_minutes": nullable(
                    integer_property("Length of the visit or service in minutes.")
                ),
                "nights": nullable(integer_property("Number of nights to stay.")),
                "notes": nullable(
                    string_property("Wishes such as a window seat or a high chair.")
                ),
            }
        ),
    ),
    AssistantToolName.CANCEL_BOOKING: (
        "Cancel a booking by its id, or by the customer's phone and the "
        "booking date, following the cancellation policy.",
        object_schema(
            {
                "booking_id": nullable(string_property("Booking id, if known.")),
                "phone": nullable(string_property(PHONE_HINT)),
                "date": nullable(string_property(DATE_HINT)),
            }
        ),
    ),
    AssistantToolName.RESCHEDULE_BOOKING: (
        "Move a booking, found by its id or by the customer's phone and old "
        "date, to a new date and time. Check availability first.",
        object_schema(
            {
                "booking_id": nullable(string_property("Booking id, if known.")),
                "phone": nullable(string_property(PHONE_HINT)),
                "old_date": nullable(string_property(DATE_HINT)),
                "new_date": string_property(DATE_HINT),
                "new_time": nullable(string_property(TIME_HINT)),
            }
        ),
    ),
    AssistantToolName.CREATE_LEAD: (
        "Pass a request that is not a simple booking to a manager: banquets, "
        "groups, corporate events, orders, viewings and anything non-standard.",
        object_schema(
            {
                "lead_type": enum_property(
                    [lead_type.value for lead_type in LeadType],
                    "Kind of request.",
                ),
                "details": string_property(
                    "Everything the manager needs, in the customer's words."
                ),
                "name": nullable(string_property("Customer's name.")),
                "phone": nullable(string_property(PHONE_HINT)),
                "requested_date": nullable(string_property(DATE_HINT)),
                "party_size": nullable(integer_property("Number of guests.")),
                "budget": nullable(string_property("Budget as the customer said.")),
            }
        ),
    ),
    AssistantToolName.HANDOFF_TO_HUMAN: (
        "Pass the conversation to a staff member when the customer asks for a "
        "person, complains, has an emergency, a sensitive or unusual request, "
        "or a handoff rule of the business applies. Then tell the customer "
        "the returned customer_message.",
        object_schema(
            {
                "reason": enum_property(
                    [reason.value for reason in MODEL_HANDOFF_REASONS],
                    "Why staff should take over.",
                ),
                "summary": string_property(
                    "Short summary for staff: who, what they want, what was said."
                ),
                "urgency": enum_property(
                    [urgency.value for urgency in HandoffUrgency],
                    "How fast staff should react.",
                ),
            }
        ),
    ),
    AssistantToolName.SEND_LINK: (
        "Get a link from the business profile (menu, map, payment, booking "
        "page, delivery, website). Send only links returned by this tool.",
        object_schema(
            {
                "kind": enum_property(
                    [kind.value for kind in BusinessLinkKind],
                    "Which link to send.",
                )
            }
        ),
    ),
    AssistantToolName.RECORD_UNANSWERED_QUESTION: (
        "Record a customer question that neither the fact table nor "
        "search_knowledge answers, so the owner can add the answer.",
        object_schema(
            {"question": string_property("The question in the customer's words.")}
        ),
    ),
}


def build_tool_definitions() -> dict[AssistantToolName, LlmToolDefinition]:
    """Definitions with schemas serialized once, deterministically."""

    return {
        tool_name: LlmToolDefinition(
            name=tool_name,
            description=LlmToolDescription(description),
            input_schema_json=LlmToolInputSchemaJson(
                json.dumps(schema, ensure_ascii=False, separators=(",", ":"))
            ),
        )
        for tool_name, (description, schema) in TOOL_SPECIFICATIONS.items()
    }
