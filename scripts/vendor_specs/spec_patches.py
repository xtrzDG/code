"""
Corrections of vendor specifications, each with its reason.

Published specifications have mistakes (broken references after a merge,
fields marked required that the API never required) and lag behind the
documentation. A patch that no longer applies (the vendor fixed it) stops
the refresh, so the correction is removed instead of silently kept.
"""

import copy
import re
from collections.abc import Mapping
from typing import cast

from scripts.vendor_specs.spec_model import (
    AddProperty,
    DefinitionPatch,
    DropProperty,
    DropPropertyKeyword,
    DropRequired,
    JsonObject,
    JsonValue,
    RepairSectionReferences,
    SpecPatch,
)

OPENAPI_SCHEMA_PREFIX: str = "#/components/schemas/"
SUFFIXED_NAME: re.Pattern[str] = re.compile(r"^(?P<base>.+)_(?P<number>\d+)$")


class StalePatchError(ValueError):
    """A patch whose target changed: the vendor fixed it, so drop the patch."""


def repair_section_references(
    components: Mapping[str, JsonValue],
    patch: RepairSectionReferences,
) -> dict[str, JsonValue]:
    names: list[str] = list(components)
    if patch.first_schema not in components:
        raise StalePatchError(f"{patch.first_schema} is no longer in the document.")

    section: list[str] = names[names.index(patch.first_schema) :]
    twins: dict[str, str] = {}
    for name in section:
        match: re.Match[str] | None = SUFFIXED_NAME.match(name)
        if match is not None and match.group("base") in components:
            twins[match.group("base")] = name

    if not twins:
        raise StalePatchError(f"No renamed twins after {patch.first_schema}.")

    repaired: dict[str, JsonValue] = dict(components)
    for name in section:
        repaired[name] = retarget(copy.deepcopy(components[name]), twins)

    return repaired


def retarget(node: JsonValue, twins: Mapping[str, str]) -> JsonValue:
    if isinstance(node, list):
        return [retarget(item, twins) for item in cast(list[JsonValue], node)]

    if not isinstance(node, dict):
        return node

    retargeted: JsonObject = {}
    for key, value in cast(JsonObject, node).items():
        if key == "$ref" and isinstance(value, str):
            name: str = value.removeprefix(OPENAPI_SCHEMA_PREFIX)
            retargeted[key] = OPENAPI_SCHEMA_PREFIX + twins.get(name, name)
        else:
            retargeted[key] = retarget(value, twins)

    return retargeted


def apply_definition_patch(definitions: JsonObject, patch: DefinitionPatch) -> None:
    definition: object = definitions.get(patch.definition)
    if not isinstance(definition, dict):
        raise StalePatchError(f"{patch.definition} is not among the definitions.")

    target: JsonObject = cast(JsonObject, definition)
    if isinstance(patch, DropRequired):
        drop_required(target, patch)
    elif isinstance(patch, AddProperty):
        properties: JsonObject = property_map(target, patch.definition)
        if patch.property_name in properties:
            raise StalePatchError(
                f"{patch.definition}.{patch.property_name} is now in the spec."
            )
        properties[patch.property_name] = patch.schema
    elif isinstance(patch, DropPropertyKeyword):
        drop_property_keyword(target, patch)
    else:
        drop_property(target, patch)


def drop_property_keyword(definition: JsonObject, patch: DropPropertyKeyword) -> None:
    properties: JsonObject = property_map(definition, patch.definition)
    schema: object = properties.get(patch.property_name)
    if not isinstance(schema, dict) or patch.keyword not in schema:
        raise StalePatchError(
            f"{patch.definition}.{patch.property_name} has no {patch.keyword}."
        )

    del cast(JsonObject, schema)[patch.keyword]


def drop_required(definition: JsonObject, patch: DropRequired) -> None:
    for schema in composed_schemas(definition):
        required: object = schema.get("required")
        if isinstance(required, list) and patch.property_name in required:
            remaining: list[object] = [
                name
                for name in cast(list[object], required)
                if name != patch.property_name
            ]
            if remaining:
                schema["required"] = remaining
            else:
                del schema["required"]
            return

    raise StalePatchError(
        f"{patch.definition}.{patch.property_name} is no longer required."
    )


def drop_property(definition: JsonObject, patch: DropProperty) -> None:
    properties: JsonObject = property_map(definition, patch.definition)
    if patch.property_name not in properties:
        raise StalePatchError(f"{patch.definition}.{patch.property_name} is gone.")

    del properties[patch.property_name]
    required: object = definition.get("required")
    if isinstance(required, list) and patch.property_name in required:
        definition["required"] = [
            name for name in cast(list[object], required) if name != patch.property_name
        ]


def property_map(definition: JsonObject, name: str) -> JsonObject:
    for schema in composed_schemas(definition):
        properties: object = schema.get("properties")
        if isinstance(properties, dict):
            return cast(JsonObject, properties)

    raise StalePatchError(f"{name} has no properties.")


def composed_schemas(definition: JsonObject) -> list[JsonObject]:
    """The definition and the inline members of its `allOf`, in order."""

    members: object = definition.get("allOf")
    inline: list[JsonObject] = (
        [
            cast(JsonObject, member)
            for member in cast(list[object], members)
            if isinstance(member, dict)
        ]
        if isinstance(members, list)
        else []
    )
    return [definition, *inline]


def describe_patch(patch: SpecPatch) -> str:
    """One line for the file's `x-vendor.patches`."""

    if isinstance(patch, RepairSectionReferences):
        return f"references from {patch.first_schema} on: {patch.reason}"

    return f"{patch.definition}.{patch.property_name}: {patch.reason}"
