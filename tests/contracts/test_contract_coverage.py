"""
The contract tree's own rules (tests/contracts/README.md): every client
package in app/clients has recorded or documented provider traffic in
tests/contracts/<package>/fixtures, every fixture is read by a test, and
every vendored specification says where it comes from - the generated ones
exactly as the refresh script's registry builds them.
"""

import json
from pathlib import Path
from typing import Any, cast
from xml.etree import ElementTree

import pytest
from jsonschema import Draft202012Validator

from scripts.vendor_specs.spec_registry import GENERATED_SPECS
from tests.contracts.contract_files import (
    CONTRACTS_DIRECTORY,
    FIXTURES_FOLDER,
    SPECS_DIRECTORY,
)

REPOSITORY_ROOT: Path = CONTRACTS_DIRECTORY.parents[1]
CLIENTS_DIRECTORY: Path = REPOSITORY_ROOT / "app" / "clients"
TESTS_DIRECTORY: Path = REPOSITORY_ROOT / "tests"
SPEC_KINDS: frozenset[str] = frozenset({"generated", "documented"})
JSON_SCHEMA_DIALECT: str = "https://json-schema.org/draft/2020-12/schema"


def client_packages() -> list[str]:
    return sorted(
        path.name
        for path in CLIENTS_DIRECTORY.iterdir()
        if path.is_dir() and (path / "__init__.py").is_file()
    )


def fixture_files() -> list[Path]:
    return sorted(
        path
        for path in CONTRACTS_DIRECTORY.glob(f"*/{FIXTURES_FOLDER}/*")
        if path.is_file()
    )


def spec_files() -> list[Path]:
    return sorted(SPECS_DIRECTORY.glob("*.json"))


def load_spec(path: Path) -> dict[str, Any]:
    return cast(dict[str, Any], json.loads(path.read_text(encoding="utf-8")))


def test_every_client_package_has_contract_fixtures() -> None:
    without: list[str] = [
        package
        for package in client_packages()
        if not any((CONTRACTS_DIRECTORY / package / FIXTURES_FOLDER).glob("*"))
    ]

    assert without == [], (
        f"Add tests/contracts/<package>/{FIXTURES_FOLDER}/ with what the "
        f"provider sends or answers for: {without}"
    )


def test_fixture_folders_belong_to_client_packages() -> None:
    folders: set[str] = {path.parent.parent.name for path in fixture_files()}

    assert folders <= set(client_packages())


@pytest.mark.parametrize(
    "path", fixture_files(), ids=lambda path: f"{path.parent.parent.name}/{path.name}"
)
def test_every_fixture_parses_and_is_read_by_a_test(path: Path) -> None:
    text: str = path.read_text(encoding="utf-8")
    if path.suffix == ".json":
        json.loads(text)
    elif path.suffix == ".xml":
        # Our own checked-in fixture, not remote input.
        ElementTree.fromstring(text)
    else:
        pytest.fail(f"Fixtures are .json or .xml: {path.name}")

    readers: list[Path] = [
        test_file
        for test_file in TESTS_DIRECTORY.rglob("*.py")
        if path.name in test_file.read_text(encoding="utf-8")
    ]
    assert readers, f"No test reads {path.parent.parent.name}/{path.name}."


@pytest.mark.parametrize("path", spec_files(), ids=lambda path: path.name)
def test_every_vendored_spec_says_where_it_comes_from(path: Path) -> None:
    spec: dict[str, Any] = load_spec(path)
    vendor: dict[str, Any] = spec["x-vendor"]
    roots: dict[str, str] = spec["x-roots"]
    definitions: dict[str, Any] = spec["$defs"]

    assert spec["$schema"] == JSON_SCHEMA_DIALECT
    assert vendor["kind"] in SPEC_KINDS
    assert vendor["provider"] in client_packages()
    assert vendor["title"]
    if vendor["kind"] == "documented":
        assert vendor["docs"], "A documented spec lists the pages it follows."
        assert spec["$comment"], "A documented spec says how it was written."
    else:
        assert vendor["source"].startswith("https://") or vendor["format"] == (
            "python-sdk"
        )
    assert roots and set(roots) <= set(definitions)
    Draft202012Validator.check_schema(
        {"$schema": JSON_SCHEMA_DIALECT, "$defs": definitions}
    )


def test_generated_specs_are_exactly_the_registry() -> None:
    generated: dict[str, dict[str, Any]] = {
        path.name: load_spec(path)
        for path in spec_files()
        if load_spec(path)["x-vendor"]["kind"] == "generated"
    }

    assert set(generated) == {spec.file_name for spec in GENERATED_SPECS}
    for spec in GENERATED_SPECS:
        vendored: dict[str, Any] = generated[spec.file_name]
        assert vendored["x-vendor"]["provider"] == spec.provider
        assert vendored["x-vendor"]["source"] == spec.source_url
        assert vendored["x-roots"] == {root.name: root.selector for root in spec.roots}


def test_every_provider_with_a_spec_has_contract_tests() -> None:
    providers: set[str] = {
        load_spec(path)["x-vendor"]["provider"] for path in spec_files()
    }

    assert all(
        any((CONTRACTS_DIRECTORY / provider).glob("test_*.py"))
        for provider in providers
    )
