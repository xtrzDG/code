"""
Building blocks of the model tools' strict JSON schemas: every property is
required, optional values are `null`, extra properties are forbidden.
"""

from app.schemas.constants.bookings import ResourceKind

type JsonSchema = dict[str, object]


def string_property(description: str) -> JsonSchema:
    return {"type": "string", "description": description}


def integer_property(description: str) -> JsonSchema:
    return {"type": "integer", "description": description}


def string_list_property(description: str) -> JsonSchema:
    return {"type": "array", "items": {"type": "string"}, "description": description}


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
SERVICE_ID: JsonSchema = nullable(
    string_property(
        "The service, package or room type to book: its id from the facts or "
        "a tool result, or its name as the customer said it; null when the "
        "customer names none (restaurant tables)."
    )
)
RESOURCE_ID: JsonSchema = nullable(
    string_property(
        "A specific master, doctor, room or table the customer asked for: its "
        "id or its name as the customer wrote it, in any script; null for "
        "whoever is free."
    )
)
