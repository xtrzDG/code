"""
The cabinet's copy of the API description (`web/openapi.json`) is current.

The cabinet's typed client is generated from it, and the launch guide's
route check reads it: a route renamed in code (a webhook, a redirect URI)
fails here until the description is exported again.
"""

import os
from collections.abc import Iterator
from pathlib import Path

import pytest

from scripts.export_openapi import (
    EmbeddedDefinitionError,
    export_openapi_document,
    require_root_resolvable_references,
)

COMMITTED_DESCRIPTION: Path = (
    Path(__file__).resolve().parents[2] / "web" / "openapi.json"
)


@pytest.fixture
def empty_environment(monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    for variable in list(os.environ):
        monkeypatch.delenv(variable)

    yield


@pytest.mark.usefixtures("empty_environment")
def test_cabinet_api_description_matches_the_api() -> None:
    assert (
        COMMITTED_DESCRIPTION.read_text(encoding="utf-8") == export_openapi_document()
    ), "Run `cd web && npm run gen:api` and commit the result."


def test_schema_local_references_are_refused() -> None:
    document: dict[str, object] = {
        "paths": {"/x": {"post": {"schema": {"$ref": "#/$defs/Hidden"}}}},
        "components": {"schemas": {"A": {"$ref": "#/components/schemas/B"}}},
    }

    with pytest.raises(EmbeddedDefinitionError, match="Hidden"):
        require_root_resolvable_references(document)

    require_root_resolvable_references(document["components"])
