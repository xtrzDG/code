"""
Closing vendor schemas for the bodies the platform sends.

Vendors leave their object schemas open (unknown fields allowed), so a
misspelled or renamed field in an outbound body would still validate. For
outbound bodies every object schema with `properties` is closed with
`unevaluatedProperties: false`, which in JSON Schema 2020-12 also sees
the properties a composition (`allOf`, `$ref`) evaluated. A schema used
as an `allOf` member is left open (the composition is closed instead),
since a closed member would reject its siblings' fields.
"""

import copy
from typing import cast

type JsonObject = dict[str, object]

DEFINITIONS_PREFIX: str = "#/$defs/"
OPEN_ENDED_KEYWORDS: frozenset[str] = frozenset(
    {"additionalProperties", "unevaluatedProperties", "patternProperties"}
)


def closed_definitions(definitions: JsonObject) -> JsonObject:
    members: set[str] = composed_member_names(definitions)
    closed: JsonObject = {}
    for name, schema in definitions.items():
        closed[name] = close_schema(copy.deepcopy(schema), is_member=name in members)

    return closed


def composed_member_names(node: object) -> set[str]:
    """Definitions referenced directly as an `allOf` member anywhere."""

    names: set[str] = set()
    if isinstance(node, list):
        for item in cast(list[object], node):
            names |= composed_member_names(item)
        return names

    if not isinstance(node, dict):
        return names

    schema: JsonObject = cast(JsonObject, node)
    for member in as_list(schema.get("allOf")):
        if isinstance(member, dict):
            reference: object = cast(JsonObject, member).get("$ref")
            if isinstance(reference, str) and reference.startswith(DEFINITIONS_PREFIX):
                names.add(reference[len(DEFINITIONS_PREFIX) :])

    for value in schema.values():
        names |= composed_member_names(value)

    return names


def close_schema(node: object, is_member: bool = False) -> object:
    if isinstance(node, list):
        return [close_schema(item) for item in cast(list[object], node)]

    if not isinstance(node, dict):
        return node

    schema: JsonObject = cast(JsonObject, node)
    for keyword, value in schema.items():
        if keyword == "allOf":
            schema[keyword] = [
                close_schema(member, is_member=True) for member in as_list(value)
            ]
        elif keyword in ("properties", "$defs", "patternProperties") and isinstance(
            value, dict
        ):
            schema[keyword] = {
                name: close_schema(child)
                for name, child in cast(JsonObject, value).items()
            }
        elif keyword not in ("enum", "const", "required", "default"):
            schema[keyword] = close_schema(value)

    has_shape: bool = "properties" in schema or "allOf" in schema
    if has_shape and not is_member and not OPEN_ENDED_KEYWORDS & schema.keys():
        schema["unevaluatedProperties"] = False

    return schema


def as_list(value: object) -> list[object]:
    return cast(list[object], value) if isinstance(value, list) else []
