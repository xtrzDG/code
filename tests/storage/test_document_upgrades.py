"""Schema versions of stored documents and the upcaster registry."""

import pytest
from base_pydantic_schemas import BaseDocument, SchemaVersion

from app.adapters.storage.document_upgrades import (
    CURRENT_SCHEMA_VERSION,
    DOCUMENT_UPCASTERS,
    StoredJsonObject,
    declared_schema_version,
    parse_schema_version,
    stored_schema_version,
    upcasters_of,
    upgrade_stored_json,
)
from app.adapters.storage.persisted_document_codec import (
    PersistedDocumentCodec,
    parse_stored_object,
)
from app.schemas.domain.example_document import ExamplePersistentDocument
from app.schemas.exceptions.storage_errors import UnreadableStoredDocumentError
from app.schemas.typings.storage.constrained_integers import (
    DocumentSchemaVersionNumber,
)
from app.schemas.typings.storage.constrained_strings import DocumentCollectionName
from app.utilities.storage.document_collection_catalog import DOCUMENT_COLLECTIONS
from tests.storage.evolution_documents import (
    NOTE_UPCASTERS,
    NOTES_COLLECTION,
    NoteV1,
    NoteV3,
)


def test_every_catalog_collection_has_a_current_version() -> None:
    assert set(CURRENT_SCHEMA_VERSION) == {
        definition.name for definition in DOCUMENT_COLLECTIONS
    }
    for definition in DOCUMENT_COLLECTIONS:
        assert issubclass(definition.document_type, BaseDocument), definition.name
        assert CURRENT_SCHEMA_VERSION[definition.name] == declared_schema_version(
            definition.document_type
        )


def test_registered_upcasters_belong_to_catalog_collections_below_current() -> None:
    for collection_name, upcasters in DOCUMENT_UPCASTERS.items():
        current = CURRENT_SCHEMA_VERSION[collection_name]
        assert all(int(version) < int(current) for version in upcasters)


def test_the_version_is_the_schema_version_default() -> None:
    assert declared_schema_version(NoteV1) == DocumentSchemaVersionNumber(1)
    assert declared_schema_version(NoteV3) == DocumentSchemaVersionNumber(3)
    assert declared_schema_version(ExamplePersistentDocument) is None


def test_upcasters_come_from_the_registry_by_collection() -> None:
    assert upcasters_of(None) == {}
    assert upcasters_of(DocumentCollectionName("not_in_catalog")) == {}
    assert upcasters_of(NOTES_COLLECTION) == DOCUMENT_UPCASTERS.get(
        NOTES_COLLECTION, {}
    )


@pytest.mark.parametrize(
    ("document", "expected"),
    [({}, 1), ({"schema_version": "1"}, 1), ({"schema_version": "12"}, 12)],
)
def test_stored_versions(document: StoredJsonObject, expected: int) -> None:
    assert stored_schema_version(document) == DocumentSchemaVersionNumber(expected)


@pytest.mark.parametrize("value", ["0", "01", "-1", "1.5", "v2", "", "١", 1, None])
def test_unreadable_versions_are_refused(value: object) -> None:
    with pytest.raises(UnreadableStoredDocumentError):
        parse_schema_version(value)


def test_a_typed_version_parses() -> None:
    assert parse_schema_version(SchemaVersion("4")) == DocumentSchemaVersionNumber(4)


def test_upgrading_never_modifies_its_input() -> None:
    original: StoredJsonObject = {"schema_version": "2", "title": "Kept"}

    upgraded = upgrade_stored_json(
        original, NOTE_UPCASTERS, DocumentSchemaVersionNumber(3)
    )

    assert original == {"schema_version": "2", "title": "Kept"}
    assert upgraded == {"schema_version": "3", "heading": "Kept"}


def test_steps_without_an_upcaster_only_move_the_version() -> None:
    upgraded = upgrade_stored_json(
        {"title": "Kept"}, NOTE_UPCASTERS, DocumentSchemaVersionNumber(2)
    )

    assert upgraded == {"schema_version": "2", "title": "Kept"}


@pytest.mark.parametrize("text", ["not json", "[1, 2]", '"text"', "null"])
def test_stored_text_must_be_a_json_object(text: str) -> None:
    with pytest.raises(UnreadableStoredDocumentError):
        parse_stored_object(text)


def test_an_unreadable_version_fails_the_read() -> None:
    codec = PersistedDocumentCodec(NoteV3, NOTES_COLLECTION, NOTE_UPCASTERS)

    with pytest.raises(UnreadableStoredDocumentError):
        codec.decode('{"schema_version": "two"}')

    with pytest.raises(UnreadableStoredDocumentError):
        codec.version_state("[]")
