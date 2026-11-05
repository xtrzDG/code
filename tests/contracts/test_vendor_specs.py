"""
The refresh script of the vendored specifications, without the network:
a cached vendor document becomes a small JSON Schema file (references
followed, annotations dropped, OpenAPI 3.0 keywords translated, patches
applied with their reasons), `--check` reports drift without writing, and
a patch the vendor made unnecessary stops the refresh. The specs read from
installed SDKs (Anthropic, ElevenLabs) must match those SDKs, so an SDK
upgrade that changes a type fails here until the files are refreshed.
"""

import json
from pathlib import Path
from typing import Any

import pytest

from scripts import refresh_vendor_specs
from scripts.vendor_specs.spec_documents import cache_name, document_version
from scripts.vendor_specs.spec_files import build_spec_file, changed_definitions
from scripts.vendor_specs.spec_model import (
    AddProperty,
    DocumentFormat,
    DropRequired,
    JsonObject,
    SchemaRoot,
    VendorSpec,
)
from scripts.vendor_specs.spec_patches import StalePatchError
from scripts.vendor_specs.spec_registry import GENERATED_SPECS
from tests.contracts.contract_files import SPECS_DIRECTORY

EXAMPLE_SPEC = VendorSpec(
    file_name="example_api.json",
    provider="example",
    title="Example pet store",
    source_url="https://vendor.example/openapi.json",
    document_format=DocumentFormat.OPENAPI,
    roots=(
        SchemaRoot("request:pets.create", "request:post /pets"),
        SchemaRoot("response:pets.create", "response:post /pets 201"),
    ),
    patches=(
        DropRequired("NewPet", "tag", reason="the API accepts a pet without a tag"),
        AddProperty(
            "Pet", "chip", {"type": "string"}, reason="documented, not yet published"
        ),
    ),
)


def vendor_document(name_field: str = "name") -> dict[str, Any]:
    """A small OpenAPI 3.0 document as a vendor publishes it."""

    return {
        "openapi": "3.0.3",
        "info": {"title": "Pets", "version": "2026-10-01"},
        "paths": {
            "/pets": {
                "post": {
                    "requestBody": {
                        "content": {
                            "application/json": {
                                "schema": {"$ref": "#/components/schemas/NewPet"}
                            }
                        }
                    },
                    "responses": {
                        "201": {
                            "description": "Created",
                            "content": {
                                "application/json": {
                                    "schema": {"$ref": "#/components/schemas/Pet"}
                                }
                            },
                        }
                    },
                }
            }
        },
        "components": {
            "schemas": {
                "NewPet": {
                    "type": "object",
                    "description": "A pet to add.",
                    "required": [name_field, "tag"],
                    "properties": {
                        name_field: {"type": "string", "example": "Rex"},
                        "tag": {"type": "string", "nullable": True},
                    },
                },
                "Pet": {
                    "allOf": [
                        {"$ref": "#/components/schemas/NewPet"},
                        {
                            "type": "object",
                            "properties": {
                                "id": {
                                    "type": "integer",
                                    "minimum": 0,
                                    "exclusiveMinimum": True,
                                },
                                "kind": {
                                    "oneOf": [
                                        {"type": "string", "enum": ["dog", "cat"]},
                                        {"type": "integer"},
                                    ]
                                },
                            },
                        },
                    ]
                },
                "Unused": {"type": "string"},
            }
        },
    }


@pytest.fixture
def folders(tmp_path: Path) -> tuple[Path, Path]:
    cache, specs = tmp_path / "cache", tmp_path / "specs"
    cache.mkdir()
    write_cached(cache, vendor_document())
    return cache, specs


def write_cached(cache: Path, document: dict[str, Any]) -> None:
    (cache / cache_name(EXAMPLE_SPEC)).write_text(json.dumps(document), "utf-8")


def refresh(cache: Path, specs: Path, check: bool = False) -> list[str]:
    return refresh_vendor_specs.refresh_spec(EXAMPLE_SPEC, specs, cache, check)


def test_a_cached_document_becomes_a_small_spec_file(
    folders: tuple[Path, Path],
) -> None:
    cache, specs = folders

    assert refresh(cache, specs) == ["(new file)"]

    written: dict[str, Any] = json.loads((specs / "example_api.json").read_text())
    definitions: dict[str, Any] = written["$defs"]
    # Only what the roots reach; the roots point at the named schemas.
    assert set(definitions) == {
        "NewPet",
        "Pet",
        "request:pets.create",
        "response:pets.create",
    }
    assert definitions["request:pets.create"] == {"$ref": "#/$defs/NewPet"}
    assert definitions["NewPet"] == {
        "type": "object",
        "required": ["name"],
        "properties": {
            "name": {"type": "string"},
            "tag": {"type": ["string", "null"]},
        },
    }
    pet_part: dict[str, Any] = definitions["Pet"]["allOf"][1]["properties"]
    assert pet_part["id"] == {"type": "integer", "exclusiveMinimum": 0}
    assert "anyOf" in pet_part["kind"] and "oneOf" not in pet_part["kind"]
    assert pet_part["chip"] == {"type": "string"}
    assert written["x-vendor"]["version"] == "2026-10-01"
    assert written["x-vendor"]["patches"] == [
        "NewPet.tag: the API accepts a pet without a tag",
        "Pet.chip: documented, not yet published",
    ]
    assert written["x-roots"] == {
        "request:pets.create": "request:post /pets",
        "response:pets.create": "response:post /pets 201",
    }


def test_check_reports_a_renamed_field_and_writes_nothing(
    folders: tuple[Path, Path],
) -> None:
    cache, specs = folders
    refresh(cache, specs)
    before: str = (specs / "example_api.json").read_text()

    assert refresh(cache, specs, check=True) == []
    write_cached(cache, vendor_document(name_field="title"))

    assert refresh(cache, specs, check=True) == ["$defs/NewPet"]
    assert (specs / "example_api.json").read_text() == before


def test_a_patch_the_vendor_made_unnecessary_stops_the_refresh() -> None:
    document: dict[str, Any] = vendor_document()
    document["components"]["schemas"]["NewPet"]["required"] = ["name"]

    with pytest.raises(StalePatchError, match="NewPet.tag"):
        build_spec_file(EXAMPLE_SPEC, document, "2026-10-02")


@pytest.mark.parametrize(
    ("change", "expected_status"),
    [("none", 0), ("renamed", 1), ("broken", 2)],
)
def test_main_exits_with_the_drift_status(
    folders: tuple[Path, Path],
    monkeypatch: pytest.MonkeyPatch,
    change: str,
    expected_status: int,
) -> None:
    cache, specs = folders
    refresh(cache, specs)
    if change == "renamed":
        write_cached(cache, vendor_document(name_field="title"))
    elif change == "broken":
        write_cached(cache, {"openapi": "3.0.3", "paths": {}})
    monkeypatch.setattr(refresh_vendor_specs, "GENERATED_SPECS", (EXAMPLE_SPEC,))

    status: int = refresh_vendor_specs.main(
        ["--check", "--cache", str(cache), "--specs", str(specs)]
    )

    assert status == expected_status


@pytest.mark.parametrize(
    "spec",
    [s for s in GENERATED_SPECS if s.document_format is DocumentFormat.PYTHON_SDK],
    ids=lambda spec: spec.provider,
)
def test_sdk_specs_match_the_installed_sdks(spec: VendorSpec) -> None:
    fresh: JsonObject = build_spec_file(spec, {}, document_version(spec, {}))
    vendored: JsonObject = json.loads((SPECS_DIRECTORY / spec.file_name).read_text())

    assert changed_definitions(vendored, fresh) == [], (
        "The installed SDK changed its types: run "
        f"uv run python -m scripts.refresh_vendor_specs --only {spec.provider}"
    )
