"""
Every golden fixture still loads with the current code, and the current
release reads documents a newer release wrote.
"""

import json
from typing import cast

import pytest
from base_pydantic_schemas import PersistentDocument

from app.adapters.storage.document_upgrades import (
    CURRENT_SCHEMA_VERSION,
    StoredJsonObject,
    upcasters_of,
    upgrade_stored_json,
)
from app.adapters.storage.persisted_document_codec import (
    PersistedDocumentCodec,
    parse_stored_object,
)
from app.schemas.typings.storage.constrained_strings import DocumentCollectionName
from app.utilities.storage.document_collection_catalog import DOCUMENT_COLLECTIONS
from tests.storage.document_evolution.evolution_files import (
    REPOSITORY_FILES,
    JsonValue,
)

GOLDEN_CASES: list[tuple[DocumentCollectionName, type[PersistentDocument], int]] = [
    (definition.name, definition.document_type, version)
    for definition in DOCUMENT_COLLECTIONS
    for version in REPOSITORY_FILES.golden_versions(definition.name)
]
CURRENT_CASES: list[tuple[DocumentCollectionName, type[PersistentDocument]]] = [
    (definition.name, definition.document_type) for definition in DOCUMENT_COLLECTIONS
]


def codec_of(
    collection_name: DocumentCollectionName,
    document_type: type[PersistentDocument],
) -> PersistedDocumentCodec[PersistentDocument]:
    return PersistedDocumentCodec(document_type, collection_name)


def current_golden(collection_name: DocumentCollectionName) -> str:
    version: int = int(CURRENT_SCHEMA_VERSION[collection_name])
    return REPOSITORY_FILES.read_golden_text(collection_name, version)


@pytest.mark.parametrize(("collection_name", "document_type", "version"), GOLDEN_CASES)
def test_every_golden_fixture_loads_with_the_current_code(
    collection_name: DocumentCollectionName,
    document_type: type[PersistentDocument],
    version: int,
) -> None:
    text: str = REPOSITORY_FILES.read_golden_text(collection_name, version)
    stored: StoredJsonObject = parse_stored_object(text)

    document = codec_of(collection_name, document_type).decode(text)

    assert stored["schema_version"] == str(version)
    current = CURRENT_SCHEMA_VERSION[collection_name]
    assert document.model_dump()["schema_version"] == str(int(current))
    # After the upcasters nothing of the old shape is left over: renamed and
    # removed fields are handled, not silently dropped by the tolerant read.
    upgraded = upgrade_stored_json(stored, upcasters_of(collection_name), current)
    assert document_type.model_validate_json(json.dumps(upgraded)) == document


@pytest.mark.parametrize(("collection_name", "document_type"), CURRENT_CASES)
def test_the_current_golden_is_complete_and_canonical(
    collection_name: DocumentCollectionName,
    document_type: type[PersistentDocument],
) -> None:
    text: str = current_golden(collection_name)
    stored: StoredJsonObject = parse_stored_object(text)
    codec = codec_of(collection_name, document_type)

    strict = document_type.model_validate_json(text)

    assert codec.decode(text) == strict
    assert parse_stored_object(codec.encode(strict)) == stored
    assert set(stored) == set(document_type.model_fields)
    # Every optional field set and every list filled, so the fixture
    # exercises every nested type of the shape.
    assert empty_paths(stored, str(collection_name)) == []


@pytest.mark.parametrize(("collection_name", "document_type"), CURRENT_CASES)
def test_this_release_reads_what_the_next_one_writes(
    collection_name: DocumentCollectionName,
    document_type: type[PersistentDocument],
) -> None:
    text: str = current_golden(collection_name)
    next_release: JsonValue = with_unknown_fields(parse_stored_object(text))
    assert isinstance(next_release, dict)
    next_document = cast(StoredJsonObject, next_release)
    next_document["schema_version"] = str(
        int(CURRENT_SCHEMA_VERSION[collection_name]) + 1
    )
    codec = codec_of(collection_name, document_type)

    assert codec.decode(json.dumps(next_document)) == codec.decode(text)


def with_unknown_fields(value: JsonValue) -> JsonValue:
    """The value with a new field in every object, as a newer release adds."""

    if isinstance(value, list):
        return [with_unknown_fields(item) for item in cast(list[JsonValue], value)]

    if isinstance(value, dict):
        expanded: StoredJsonObject = {
            key: with_unknown_fields(item)
            for key, item in cast(StoredJsonObject, value).items()
        }
        expanded["field_of_the_next_release"] = {"nested": [1, "two", None]}
        return expanded

    return value


def empty_paths(value: JsonValue, path: str) -> list[str]:
    if value is None or value == [] or value == {}:
        return [path]

    if isinstance(value, list):
        items: list[JsonValue] = cast(list[JsonValue], value)
        return [
            empty
            for position, item in enumerate(items)
            for empty in empty_paths(item, f"{path}[{position}]")
        ]

    if isinstance(value, dict):
        return [
            empty
            for key, item in cast(StoredJsonObject, value).items()
            for empty in empty_paths(item, f"{path}.{key}")
        ]

    return []
