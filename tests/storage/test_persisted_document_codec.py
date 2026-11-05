"""Strict writes, tolerant and upcasting reads of stored documents."""

import json

import pytest
from base_pydantic_schemas import SchemaVersion
from pydantic import ValidationError

from app.adapters.storage.document_upgrades import StoredJsonObject
from app.adapters.storage.in_memory_document_collection import (
    InMemoryDocumentCollectionAdapter,
)
from app.adapters.storage.persisted_document_codec import (
    PersistedDocumentCodec,
    parse_stored_object,
)
from app.schemas.constants.storage import StoredDocumentVersionState
from app.schemas.domain.example_document import ExamplePersistentDocument
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.integers import ExampleInt
from app.schemas.typings.knowledge.strings import KnowledgeTitle
from app.schemas.typings.storage.constrained_integers import (
    DocumentSchemaVersionNumber,
)
from tests.storage.evolution_documents import (
    NOTE_UPCASTERS,
    NOTES_COLLECTION,
    NoteV1,
    NoteV2,
    NoteV3,
    build_note_v1,
    build_note_v2,
)

V2_CODEC = PersistedDocumentCodec(NoteV2, NOTES_COLLECTION, NOTE_UPCASTERS)
V3_CODEC = PersistedDocumentCodec(NoteV3, NOTES_COLLECTION, NOTE_UPCASTERS)


def stored(document: NoteV1 | NoteV2 | NoteV3) -> StoredJsonObject:
    return parse_stored_object(document.model_dump_json())


def test_a_round_trip_returns_an_equal_document() -> None:
    note = build_note_v2(BusinessId())

    assert V2_CODEC.decode(V2_CODEC.encode(note)) == note
    assert V2_CODEC.current_version == DocumentSchemaVersionNumber(2)


def test_writes_stamp_the_current_version() -> None:
    note = build_note_v2(BusinessId()).model_copy(
        update={"schema_version": SchemaVersion("1")}
    )

    written = json.loads(V2_CODEC.encode(note))

    assert written["schema_version"] == "2"
    assert written["title"] == "Opening hours"


def test_the_old_release_reads_what_the_next_one_wrote() -> None:
    # Release N - 1 meets a row release N wrote during a rolling deploy:
    # unknown fields (also of nested objects) are ignored, nothing fails.
    v2_text = V2_CODEC.encode(build_note_v2(BusinessId()))
    old_codec = PersistedDocumentCodec(NoteV1, NOTES_COLLECTION)

    note = old_codec.decode(v2_text)

    assert note.title == KnowledgeTitle("Opening hours")
    assert [str(label.key) for label in note.labels] == ["season"]
    assert note.schema_version == SchemaVersion("1")
    assert json.loads(old_codec.encode(note))["schema_version"] == "1"
    assert old_codec.version_state(v2_text) is StoredDocumentVersionState.NEWER


def test_the_new_release_reads_old_rows_without_an_upcaster() -> None:
    v1_text = PersistedDocumentCodec(NoteV1, NOTES_COLLECTION).encode(
        build_note_v1(BusinessId())
    )

    note = V2_CODEC.decode(v1_text)

    assert note.pin_order is None
    assert note.labels[0].caption is None
    assert note.schema_version == SchemaVersion("2")
    assert V2_CODEC.version_state(v1_text) is StoredDocumentVersionState.OLDER


def test_upcasters_run_step_by_step_up_to_the_current_version() -> None:
    v1_text = json.dumps(stored(build_note_v1(BusinessId())))

    note = V3_CODEC.decode(v1_text)

    assert note.heading == KnowledgeTitle("Opening hours")
    assert note.schema_version == SchemaVersion("3")
    upgraded = json.loads(V3_CODEC.upgrade(v1_text))
    assert upgraded["schema_version"] == "3"
    assert "title" not in upgraded
    assert upgraded["heading"] == "Opening hours"


def test_an_old_row_that_validates_as_it_is_is_still_upcast() -> None:
    # A v2 row with `heading` already present (and `title`) must not skip
    # the upcaster just because it happens to validate.
    row = stored(build_note_v2(BusinessId()))
    row["heading"] = "Stale heading"

    note = V3_CODEC.decode(json.dumps(row))

    assert note.heading == KnowledgeTitle("Opening hours")


def test_newer_rows_are_read_tolerantly_but_never_upcast() -> None:
    row = stored(build_note_v2(BusinessId()))
    row["schema_version"] = "7"
    row["brand_new_field"] = {"nested": [1, 2, 3]}

    note = V2_CODEC.decode(json.dumps(row))

    assert note.schema_version == SchemaVersion("2")
    assert note.pin_order == ExampleInt(3)


def test_tolerant_reads_still_validate_types_and_required_fields() -> None:
    wrong_type = stored(build_note_v2(BusinessId()))
    wrong_type["pin_order"] = "three"
    missing = stored(build_note_v2(BusinessId()))
    del missing["business_id"]

    for row in (wrong_type, missing):
        with pytest.raises(ValidationError):
            V2_CODEC.decode(json.dumps(row))


def test_inputs_and_dtos_keep_forbidding_unknown_fields() -> None:
    row = stored(build_note_v2(BusinessId()))
    row["unknown"] = True

    with pytest.raises(ValidationError, match="Extra inputs are not permitted"):
        NoteV2.model_validate_json(json.dumps(row))

    assert V2_CODEC.decode(json.dumps(row)).title == KnowledgeTitle("Opening hours")


def test_unversioned_documents_are_read_tolerantly_and_written_as_they_are() -> None:
    codec = PersistedDocumentCodec(ExamplePersistentDocument, None)
    text = json.dumps(
        {
            "count": 2,
            "name": "plain",
            "random_id": "6f4f3a44-4c8e-4a8e-9d43-5bfbcd5a6b4b",
            "added_later": True,
        }
    )

    document = codec.decode(text)

    assert codec.current_version is None
    assert codec.version_state(text) is StoredDocumentVersionState.CURRENT
    assert "schema_version" not in json.loads(codec.encode(document))


def test_a_codec_without_upcasters_uses_the_registered_ones() -> None:
    registered = PersistedDocumentCodec(NoteV1, NOTES_COLLECTION)
    text = registered.encode(build_note_v1(BusinessId()))

    assert registered.version_state(text) is StoredDocumentVersionState.CURRENT
    assert registered.decode(text) == registered.decode(registered.upgrade(text))


def test_in_memory_collections_write_and_read_through_the_codec() -> None:
    notes = InMemoryDocumentCollectionAdapter[NoteV2](NoteV2)
    note = build_note_v2(BusinessId()).model_copy(
        update={"schema_version": SchemaVersion("1")}
    )

    notes.upsert(str(note.id), note)
    loaded = notes.get(str(note.id))

    assert loaded is not None
    assert loaded.schema_version == SchemaVersion("2")
    assert loaded.pin_order == note.pin_order
