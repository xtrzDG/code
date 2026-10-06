"""
Vendor schemas as JSON Schema 2020-12, with only what validation needs.

- References point into the file's own `$defs` ("#/$defs/<Name>");
  `extract_definitions` follows them from the roots and copies every
  schema reached, nothing else.
- Annotations (descriptions, examples, titles, vendor `x-` extensions)
  are dropped: the files stay small and change only when a shape does.
- OpenAPI 3.0 keywords become their JSON Schema forms: `nullable` adds
  "null" to the type; boolean `exclusiveMinimum`/`exclusiveMaximum` turn
  the bound exclusive.
- `oneOf` becomes `anyOf`: OpenAPI picks a variant by its discriminator,
  while JSON Schema demands that exactly one variant matches, which
  overlapping open variants never satisfy.
- An `allOf` member closed with `additionalProperties: false` closes the
  composition instead (`unevaluatedProperties: false` on the parent), the
  meaning vendors intend: closed member by member, no instance could pass.
"""

from collections.abc import Callable, Mapping
from typing import cast

from scripts.vendor_specs.spec_model import JsonObject, JsonValue

DEFINITIONS_PREFIX: str = "#/$defs/"
DROPPED_KEYWORDS: frozenset[str] = frozenset(
    {
        "$schema",
        "annotations",
        "deprecated",
        "description",
        "discriminator",
        "enumDescriptions",
        "example",
        "examples",
        "externalDocs",
        "id",
        "readOnly",
        "title",
        "writeOnly",
        "xml",
    }
)
# Keywords whose values are data, not schemas.
LITERAL_KEYWORDS: frozenset[str] = frozenset({"const", "default", "enum", "required"})
# Keywords whose values map names to schemas.
SCHEMA_MAP_KEYWORDS: frozenset[str] = frozenset(
    {"$defs", "definitions", "patternProperties", "properties"}
)

type ReferenceResolver = Callable[[str], str]


class UnknownReferenceError(ValueError):
    """A reference the extraction cannot follow inside the vendor document."""


def openapi_reference(reference: str) -> str:
    """ "#/components/schemas/Event" -> "Event"."""

    prefix: str = "#/components/schemas/"
    if not reference.startswith(prefix):
        raise UnknownReferenceError(f"Unsupported reference {reference!r}.")

    return reference[len(prefix) :]


def definitions_reference(reference: str) -> str:
    """ "#/$defs/Event" (pydantic) -> "Event"."""

    if not reference.startswith(DEFINITIONS_PREFIX):
        raise UnknownReferenceError(f"Unsupported reference {reference!r}.")

    return reference[len(DEFINITIONS_PREFIX) :]


def discovery_reference(reference: str) -> str:
    """Google discovery documents name schemas directly: "Event"."""

    return reference


class SchemaConverter:
    """Converts schemas of one vendor document, remembering the names reached."""

    def __init__(
        self,
        components: Mapping[str, JsonValue],
        resolve_reference: ReferenceResolver,
    ) -> None:
        self._components: Mapping[str, JsonValue] = components
        self._resolve_reference: ReferenceResolver = resolve_reference
        self._reached: list[str] = []

    def convert(self, node: JsonValue) -> JsonValue:
        if isinstance(node, list):
            return [self.convert(item) for item in cast(list[JsonValue], node)]

        if not isinstance(node, dict):
            return node

        source: JsonObject = cast(JsonObject, node)
        converted: JsonObject = {}
        for keyword, value in source.items():
            if keyword in DROPPED_KEYWORDS or keyword.startswith("x-"):
                continue

            if keyword == "$ref":
                converted["$ref"] = self._reference(str(value))
            elif keyword in LITERAL_KEYWORDS:
                converted[keyword] = value
            elif keyword in SCHEMA_MAP_KEYWORDS and isinstance(value, dict):
                schemas: JsonObject = cast(JsonObject, value)
                converted[keyword] = {
                    name: self.convert(schema) for name, schema in schemas.items()
                }
            elif keyword != "nullable":
                converted[keyword] = self.convert(value)

        return normalize_keywords(converted, source.get("nullable") is True)

    def extract_definitions(self, roots: Mapping[str, JsonValue]) -> JsonObject:
        """The converted roots and every schema they reach, sorted by name."""

        definitions: JsonObject = {
            name: self.convert(schema) for name, schema in roots.items()
        }
        while self._reached:
            name: str = self._reached.pop()
            if name in definitions:
                continue

            definitions[name] = {}
            definitions[name] = self.convert(self._components[name])

        return dict(sorted(definitions.items()))

    def _reference(self, reference: str) -> str:
        name: str = self._resolve_reference(reference)
        if name not in self._components:
            raise UnknownReferenceError(f"{reference!r} names no schema.")

        self._reached.append(name)
        return DEFINITIONS_PREFIX + name


def normalize_keywords(schema: JsonObject, is_nullable: bool) -> JsonObject:
    if "oneOf" in schema:
        schema["anyOf"] = schema.pop("oneOf")

    for bound in ("Minimum", "Maximum"):
        exclusive: object = schema.get(f"exclusive{bound}")
        if isinstance(exclusive, bool):
            del schema[f"exclusive{bound}"]
            if exclusive and bound.lower() in schema:
                schema[f"exclusive{bound}"] = schema.pop(bound.lower())

    members: object = schema.get("allOf")
    if isinstance(members, list):
        for member in cast(list[object], members):
            if not isinstance(member, dict):
                continue

            closed_member: JsonObject = cast(JsonObject, member)
            if closed_member.get("additionalProperties") is False:
                del closed_member["additionalProperties"]
                schema["unevaluatedProperties"] = False

    if not is_nullable:
        return schema

    schema_type: object = schema.get("type")
    if isinstance(schema_type, str):
        schema["type"] = [schema_type, "null"]
        return schema

    if isinstance(schema_type, list):
        schema["type"] = [*cast(list[object], schema_type), "null"]
        return schema

    return {"anyOf": [schema, {"type": "null"}]}
