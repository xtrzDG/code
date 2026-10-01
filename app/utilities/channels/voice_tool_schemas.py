"""Tool argument schemas in the format of ElevenLabs webhook tools.

The chat offers tools to the language model with JSON Schema. ElevenLabs
accepts a narrower dialect: every property has a type and a description
(what the model should fill in), arrays have `items`, enums are string-only,
and keywords such as `additionalProperties` or `minimum` are not allowed.
The conversion keeps names, types, descriptions, enums and required fields.
"""

from typing import cast

from app.utilities.channels.json_values import (
    JsonObject,
    as_object,
    read_object,
    read_strings,
    read_text,
)

LITERAL_TYPES: frozenset[str] = frozenset({"string", "integer", "number", "boolean"})
NULL_TYPE: str = "null"
DEFAULT_TYPE: str = "string"
MAX_SCHEMA_DEPTH: int = 8


def convert_tool_schema(schema: JsonObject, description: str) -> JsonObject:
    """The arguments object of a tool, converted; non-objects become empty."""

    converted: JsonObject = convert_property(schema, description, depth=0)
    if converted.get("type") != "object":
        return {"type": "object", "description": description, "properties": {}}

    return converted


def convert_property(
    node: JsonObject, fallback_description: str, depth: int
) -> JsonObject:
    """Convert one JSON Schema node (property, array item or object)."""

    resolved: JsonObject = resolve_variant(node)
    description: str = describe(resolved, fallback_description)
    schema_type: str = read_schema_type(resolved)
    if depth >= MAX_SCHEMA_DEPTH:
        return {"type": DEFAULT_TYPE, "description": description}

    if schema_type == "object":
        return convert_object(resolved, description, depth)

    if schema_type == "array":
        items: JsonObject = read_object(resolved, "items") or {"type": DEFAULT_TYPE}
        return {
            "type": "array",
            "description": description,
            "items": convert_property(items, f"one {fallback_description}", depth + 1),
        }

    converted: JsonObject = {"type": schema_type, "description": description}
    enum_values: list[str] = read_enum(resolved)
    if schema_type == "string" and enum_values:
        converted["enum"] = enum_values

    return converted


def convert_object(node: JsonObject, description: str, depth: int) -> JsonObject:
    properties_node: JsonObject = read_object(node, "properties") or {}
    properties: JsonObject = {}
    for property_name, property_node in properties_node.items():
        property_object: JsonObject | None = as_object(property_node)
        if property_object is None:
            continue

        properties[property_name] = convert_property(
            property_object,
            humanize(property_name),
            depth + 1,
        )

    required: list[str] = [
        property_name
        for property_name in read_strings(node, "required")
        if property_name in properties
    ]
    converted: JsonObject = {
        "type": "object",
        "description": description,
        "properties": properties,
    }
    if required:
        converted["required"] = required

    return converted


def resolve_variant(node: JsonObject) -> JsonObject:
    """First typed alternative of anyOf / oneOf (nullable fields)."""

    for keyword in ("anyOf", "oneOf"):
        variants: object = node.get(keyword)
        if not isinstance(variants, list):
            continue

        for variant in cast(list[object], variants):
            variant_object: JsonObject | None = as_object(variant)
            if variant_object is None:
                continue

            if read_schema_type(variant_object, allow_null=True) != NULL_TYPE:
                merged: JsonObject = dict(variant_object)
                if "description" not in merged and "description" in node:
                    merged["description"] = node["description"]
                return merged

    return node


def read_schema_type(node: JsonObject, allow_null: bool = False) -> str:
    raw_type: object = node.get("type")
    candidates: list[str] = []
    if isinstance(raw_type, str):
        candidates = [raw_type]
    elif isinstance(raw_type, list):
        candidates = [
            item for item in cast(list[object], raw_type) if isinstance(item, str)
        ]

    for candidate in candidates:
        if candidate == NULL_TYPE and allow_null and len(candidates) == 1:
            return NULL_TYPE

        if candidate in LITERAL_TYPES or candidate in ("object", "array"):
            return candidate

    if "properties" in node:
        return "object"

    if "items" in node:
        return "array"

    return DEFAULT_TYPE


def read_enum(node: JsonObject) -> list[str]:
    values: object = node.get("enum")
    if not isinstance(values, list):
        return []

    return [
        value
        for value in cast(list[object], values)
        if isinstance(value, str) and value != ""
    ]


def describe(node: JsonObject, fallback_description: str) -> str:
    """The node's description (with its format hint) or the fallback."""

    description: str = read_text(node, "description") or fallback_description
    value_format: str | None = read_text(node, "format")
    if value_format is not None and value_format not in description:
        description = f"{description} (format: {value_format})"

    return description


def humanize(property_name: str) -> str:
    """ "party_size" -> "party size": a description when the schema has none."""

    return property_name.replace("_", " ").strip() or "value"
