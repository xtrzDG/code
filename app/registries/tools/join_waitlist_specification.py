"""The join_waitlist model tool: a wish kept for a freed place."""

from app.registries.tools.tool_schema_parts import (
    DATE_HINT,
    RESOURCE_ID,
    RESOURCE_TYPE,
    SERVICE_ID,
    TIME_HINT,
    JsonSchema,
    integer_property,
    nullable,
    object_schema,
    string_property,
)

JOIN_WAITLIST_SPECIFICATION: tuple[str, JsonSchema] = (
    "Put the customer on the waitlist for a day with no free time, only after "
    "check_availability returned no slots with waitlist_open true and the "
    "customer agreed. When a place frees up the business offers it to the "
    "customer in this conversation, held for a short time; promise nothing "
    "more. Give the customer's name and the window of time they can come.",
    object_schema(
        {
            "name": string_property("Name to offer the place under."),
            "service_id": SERVICE_ID,
            "resource_id": RESOURCE_ID,
            "resource_type": RESOURCE_TYPE,
            "date": string_property(DATE_HINT),
            "time_from": nullable(
                string_property("Earliest start that suits. " + TIME_HINT)
            ),
            "time_to": nullable(
                string_property("Latest start that suits. " + TIME_HINT)
            ),
            "party_size": integer_property("Number of guests."),
            "nights": nullable(integer_property("Number of nights to stay.")),
            "notes": nullable(string_property("Wishes for the place, if any.")),
        }
    ),
)
