"""
Write the API's OpenAPI document as JSON (for the web cabinet's typed client):

    uv run python -m scripts.export_openapi web/openapi.json

Without a path the document goes to standard output.

Some request bodies are JSON Schemas with their own `$id` and `$defs`, so
their "#/$defs/..." references resolve inside the schema (JSON Schema
2020-12). Code generators resolve references from the document root, so the
exported document has those references inlined; the API itself is unchanged.
"""

import json
import sys
from pathlib import Path
from typing import cast

from app.main import create_application

LOCAL_DEFINITION_PREFIX: str = "#/$defs/"


class RecursiveDefinitionError(ValueError):
    """A schema definition refers to itself and cannot be inlined."""


def export_openapi_document() -> str:
    """The OpenAPI document of the application, pretty-printed, keys sorted."""

    document: object = create_application().openapi()
    portable_document: object = inline_embedded_definitions(document, {}, ())
    return (
        json.dumps(portable_document, ensure_ascii=False, indent=2, sort_keys=True)
        + "\n"
    )


def inline_embedded_definitions(
    node: object,
    definitions: dict[str, object],
    expanding: tuple[str, ...],
) -> object:
    """
    Replace "#/$defs/<name>" references with the definitions of the nearest
    enclosing schema that declares `$defs`; drop every `$defs` and `$id`
    (only the request schemas above carry them).
    """

    if isinstance(node, list):
        return [
            inline_embedded_definitions(item, definitions, expanding)
            for item in cast(list[object], node)
        ]

    if not isinstance(node, dict):
        return node

    mapping: dict[str, object] = cast(dict[str, object], node)
    scope: dict[str, object] = definitions
    embedded: object = mapping.get("$defs")
    if isinstance(embedded, dict):
        scope = definitions | cast(dict[str, object], embedded)

    reference: object = mapping.get("$ref")
    if isinstance(reference, str) and reference.startswith(LOCAL_DEFINITION_PREFIX):
        name: str = reference.removeprefix(LOCAL_DEFINITION_PREFIX)
        if name in expanding:
            raise RecursiveDefinitionError(f"Definition {name!r} refers to itself.")

        definition: object = inline_embedded_definitions(
            scope[name], scope, (*expanding, name)
        )
        siblings: dict[str, object] = {
            key: inline_embedded_definitions(value, scope, expanding)
            for key, value in mapping.items()
            if key not in ("$ref", "$defs", "$id")
        }
        if isinstance(definition, dict):
            return cast(dict[str, object], definition) | siblings

        return definition

    return {
        key: inline_embedded_definitions(value, scope, expanding)
        for key, value in mapping.items()
        if key not in ("$defs", "$id")
    }


def main(arguments: list[str]) -> None:
    document_text: str = export_openapi_document()
    if not arguments:
        sys.stdout.write(document_text)
        return

    output_path = Path(arguments[0])
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(document_text, encoding="utf-8")


if __name__ == "__main__":
    main(sys.argv[1:])
