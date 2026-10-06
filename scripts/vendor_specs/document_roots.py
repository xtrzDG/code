"""
Finding the roots of a vendored file in its vendor document, and the
named schemas their references reach (`SchemaRoot.selector`).
"""

import importlib
from collections.abc import Mapping
from dataclasses import dataclass
from typing import cast

from pydantic import TypeAdapter

from scripts.vendor_specs.schema_conversion import (
    ReferenceResolver,
    definitions_reference,
    discovery_reference,
    openapi_reference,
)
from scripts.vendor_specs.spec_model import (
    DocumentFormat,
    JsonObject,
    JsonValue,
    SchemaRoot,
)

# Request body media types in the order the clients send them.
REQUEST_MEDIA_TYPES: tuple[str, ...] = (
    "application/json",
    "application/x-www-form-urlencoded",
    "multipart/form-data",
)


class SelectorError(ValueError):
    """A selector that names nothing in the vendor document."""


@dataclass(frozen=True)
class DocumentSchemas:
    """The raw roots of a file, the schemas they may reach, and their naming."""

    roots: dict[str, JsonValue]
    components: Mapping[str, JsonValue]
    resolve_reference: ReferenceResolver


def openapi_schemas(
    document: JsonObject,
    components: Mapping[str, JsonValue],
    roots: tuple[SchemaRoot, ...],
) -> DocumentSchemas:
    return DocumentSchemas(
        roots={root.name: openapi_root(document, components, root) for root in roots},
        components=components,
        resolve_reference=openapi_reference,
    )


def openapi_components(document: JsonObject) -> dict[str, JsonValue]:
    return dict(child(child(document, "components"), "schemas"))


def openapi_root(
    document: JsonObject,
    components: Mapping[str, JsonValue],
    root: SchemaRoot,
) -> JsonValue:
    kind, _, target = root.selector.partition(":")
    if kind == "schema":
        return named(components, target)

    method, _, rest = target.partition(" ")
    if kind == "request":
        path: str = rest
        operation: JsonObject = child(
            child(child(document, "paths"), path), method.lower()
        )
        body: JsonObject = child(operation, "requestBody")
        content: JsonObject = child(body, "content")
        for media_type in REQUEST_MEDIA_TYPES:
            if media_type in content:
                return child(child(content, media_type), "schema")

        raise SelectorError(f"{root.selector}: no request body the clients send.")

    if kind == "response":
        path, _, status = rest.rpartition(" ")
        operation = child(child(child(document, "paths"), path), method.lower())
        response: JsonObject = child(child(operation, "responses"), status)
        return child(child(child(response, "content"), "application/json"), "schema")

    raise SelectorError(f"Unknown selector {root.selector!r}.")


def discovery_schemas(
    document: JsonObject,
    roots: tuple[SchemaRoot, ...],
) -> DocumentSchemas:
    components: JsonObject = child(document, "schemas")
    return DocumentSchemas(
        roots={
            root.name: named(components, root.selector.removeprefix("schema:"))
            for root in roots
        },
        components=components,
        resolve_reference=discovery_reference,
    )


def sdk_schemas(roots: tuple[SchemaRoot, ...]) -> DocumentSchemas:
    """Roots from the SDK's types; pydantic names their shared parts."""

    raw_roots: dict[str, JsonValue] = {}
    components: dict[str, JsonValue] = {}
    for root in roots:
        _, module_name, type_name = root.selector.split(":")
        sdk_type: object = getattr(importlib.import_module(module_name), type_name)
        schema: JsonObject = TypeAdapter(sdk_type).json_schema(
            ref_template="#/$defs/{model}"
        )
        for name, definition in child(schema, "$defs").items():
            if components.get(name, definition) != definition:
                raise SelectorError(f"{name} differs between the SDK's types.")
            components[name] = definition

        raw_roots[root.name] = {
            key: value for key, value in schema.items() if key != "$defs"
        }

    return DocumentSchemas(
        roots=raw_roots,
        components=components,
        resolve_reference=definitions_reference,
    )


def schemas_of(
    document_format: DocumentFormat,
    document: JsonObject,
    components: Mapping[str, JsonValue],
    roots: tuple[SchemaRoot, ...],
) -> DocumentSchemas:
    if document_format is DocumentFormat.OPENAPI:
        return openapi_schemas(document, components, roots)

    if document_format is DocumentFormat.GOOGLE_DISCOVERY:
        return discovery_schemas(document, roots)

    return sdk_schemas(roots)


def named(components: Mapping[str, JsonValue], name: str) -> JsonValue:
    if name not in components:
        raise SelectorError(f"The document has no schema {name!r}.")

    return components[name]


def child(node: Mapping[str, JsonValue], key: str) -> JsonObject:
    value: JsonValue = node.get(key)
    if not isinstance(value, dict):
        if key == "$defs":
            return {}
        raise SelectorError(f"{key!r} is missing from the vendor document.")

    return cast(JsonObject, value)
