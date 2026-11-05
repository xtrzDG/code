"""
Write the API's OpenAPI document as JSON (for the web cabinet's typed client):

    uv run python -m scripts.export_openapi web/openapi.json

Without a path the document goes to standard output.

Request bodies are described with their nested models inlined
(`describe_json_body` in app/gateways/http/strict_request_parsing.py), so
code generators, which resolve references from the document root, read the
document as is. The export refuses a document that still carries a
schema-local "#/$defs/..." reference.
"""

import json
import sys
from pathlib import Path
from typing import cast

from app.main import create_application

LOCAL_DEFINITION_PREFIX: str = "#/$defs/"


class EmbeddedDefinitionError(ValueError):
    """A schema-local reference that root-resolving generators cannot follow."""


def export_openapi_document() -> str:
    """The OpenAPI document of the application, pretty-printed, keys sorted."""

    document: object = create_application().openapi()
    require_root_resolvable_references(document)
    return json.dumps(document, ensure_ascii=False, indent=2, sort_keys=True) + "\n"


def require_root_resolvable_references(node: object) -> None:
    """
    Raises:
        EmbeddedDefinitionError: a "$ref" points into a schema's own `$defs`.
    """

    if isinstance(node, list):
        for item in cast(list[object], node):
            require_root_resolvable_references(item)
        return

    if not isinstance(node, dict):
        return

    mapping: dict[str, object] = cast(dict[str, object], node)
    reference: object = mapping.get("$ref")
    if isinstance(reference, str) and reference.startswith(LOCAL_DEFINITION_PREFIX):
        raise EmbeddedDefinitionError(
            f"{reference!r} is local to its schema; describe the body with "
            "describe_json_body so nested models are inlined."
        )

    for value in mapping.values():
        require_root_resolvable_references(value)


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
