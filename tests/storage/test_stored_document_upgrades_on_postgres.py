"""`migrate-documents` on a real table: batches, idempotence, concurrent writes."""

import pytest

from app.adapters.storage.document_upgrades import StoredJsonObject
from app.adapters.storage.persisted_document_codec import parse_stored_object
from app.adapters.storage.postgres.postgres_stored_document_upgrade_adapter import (
    PostgresStoredDocumentUpgradeAdapter,
    read_position,
)
from app.clients.postgres.postgres_connection_pool_client import (
    PostgresConnectionPoolClient,
)
from app.schemas.domain.example_document import ExamplePersistentDocument
from app.schemas.dto.document_upgrades import CollectionUpgradeRequest
from app.schemas.exceptions.application_errors import NotFoundError
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.knowledge.prefixed_id import KnowledgeItemId
from app.schemas.typings.storage.constrained_integers import (
    DocumentCount,
    DocumentSchemaVersionNumber,
    DocumentUpgradeBatchSize,
)
from app.schemas.typings.storage.constrained_strings import DocumentCollectionName
from app.schemas.typings.storage.strings import StoredDocumentKey
from app.utilities.storage.document_collection_definition import (
    DocumentCollectionDefinition,
)
from tests.storage.evolution_documents import (
    NOTE_UPCASTERS,
    NOTES_COLLECTION,
    NoteV2,
    NoteV3,
    build_note_v1,
    build_note_v2,
)
from tests.storage.stored_rows import (
    read_stored,
    read_updated_at,
    write_stored,
)

BUSINESS_ID: BusinessId = BusinessId()


def seed_rows(connection_pool: PostgresConnectionPoolClient) -> dict[str, str]:
    """Rows of three releases and one broken row; keys by what they are."""

    keys: dict[str, str] = {}
    for position, name in enumerate(["old_a", "old_b", "old_c"], start=10):
        note = build_note_v1(BUSINESS_ID)
        keys[name] = str(note.id)
        write_stored(
            connection_pool,
            keys[name],
            BUSINESS_ID,
            parse_stored_object(note.model_dump_json()),
            written_at=position,
        )

    current = build_note_v2(BUSINESS_ID)
    keys["current"] = str(current.id)
    write_stored(
        connection_pool,
        keys["current"],
        BUSINESS_ID,
        parse_stored_object(current.model_dump_json()),
        written_at=20,
    )
    newer: StoredJsonObject = parse_stored_object(current.model_dump_json())
    newer.update({"id": str(KnowledgeItemId()), "schema_version": "9", "x": 1})
    keys["newer"] = str(newer["id"])
    write_stored(connection_pool, keys["newer"], BUSINESS_ID, newer, written_at=30)
    broken: StoredJsonObject = parse_stored_object(
        build_note_v1(BUSINESS_ID).model_dump_json()
    )
    del broken["title"]
    keys["broken"] = str(broken["id"])
    write_stored(connection_pool, keys["broken"], BUSINESS_ID, broken, written_at=40)
    return keys


def notes_upgrades(
    connection_pool: PostgresConnectionPoolClient,
    document_type: type[NoteV2] | type[NoteV3] = NoteV2,
) -> PostgresStoredDocumentUpgradeAdapter:
    return PostgresStoredDocumentUpgradeAdapter(
        connection_pool,
        collections=[DocumentCollectionDefinition(NOTES_COLLECTION, document_type)],
        upcasters={NOTES_COLLECTION: NOTE_UPCASTERS},
    )


def request(is_dry_run: bool = False) -> CollectionUpgradeRequest:
    return CollectionUpgradeRequest(
        collection_name=NOTES_COLLECTION,
        batch_size=DocumentUpgradeBatchSize(2),
        is_dry_run=is_dry_run,
    )


def test_outdated_rows_are_rewritten_batch_by_batch_and_only_once(
    connection_pool: PostgresConnectionPoolClient,
) -> None:
    keys = seed_rows(connection_pool)
    upgrades = notes_upgrades(connection_pool)

    first = upgrades.upgrade_collection(request())
    second = upgrades.upgrade_collection(request())

    assert first.current_version == DocumentSchemaVersionNumber(2)
    assert (first.outdated, first.upgraded, first.newer, first.failed) == (
        DocumentCount(5),
        DocumentCount(3),
        DocumentCount(1),
        DocumentCount(1),
    )
    assert first.failed_document_keys == [StoredDocumentKey(keys["broken"])]
    for name in ("old_a", "old_b", "old_c"):
        assert read_stored(connection_pool, keys[name])["schema_version"] == "2"
        # A shape change is not a content change.
        assert read_updated_at(connection_pool, keys[name]) < 20
    assert read_stored(connection_pool, keys["newer"])["schema_version"] == "9"
    assert (second.outdated, second.upgraded) == (DocumentCount(2), DocumentCount(0))


def test_a_dry_run_counts_without_writing(
    connection_pool: PostgresConnectionPoolClient,
) -> None:
    keys = seed_rows(connection_pool)

    report = notes_upgrades(connection_pool).upgrade_collection(request(True))

    assert report.upgraded == DocumentCount(3)
    assert read_stored(connection_pool, keys["old_a"])["schema_version"] == "1"


def test_upcasters_rewrite_renamed_fields(
    connection_pool: PostgresConnectionPoolClient,
) -> None:
    keys = seed_rows(connection_pool)

    report = notes_upgrades(connection_pool, NoteV3).upgrade_collection(request())

    # The current v2 row is outdated now too; the broken one still fails.
    assert (report.upgraded, report.failed) == (DocumentCount(4), DocumentCount(1))
    upgraded = read_stored(connection_pool, keys["old_a"])
    assert upgraded["schema_version"] == "3"
    assert upgraded["heading"] == "Opening hours"
    assert "title" not in upgraded


def test_a_row_the_application_rewrote_meanwhile_is_left_to_it(
    connection_pool: PostgresConnectionPoolClient,
) -> None:
    note = build_note_v1(BUSINESS_ID)
    key = str(note.id)
    write_stored(
        connection_pool, key, BUSINESS_ID, parse_stored_object(note.model_dump_json())
    )
    fresh: StoredJsonObject = parse_stored_object(
        build_note_v2(BUSINESS_ID).model_dump_json()
    )
    fresh.update({"id": key, "title": "Written by the application"})

    def upcast_while_the_application_writes(
        document: StoredJsonObject,
    ) -> StoredJsonObject:
        write_stored(connection_pool, key, BUSINESS_ID, fresh)
        return document

    upgrades = PostgresStoredDocumentUpgradeAdapter(
        connection_pool,
        collections=[DocumentCollectionDefinition(NOTES_COLLECTION, NoteV2)],
        upcasters={
            NOTES_COLLECTION: {
                DocumentSchemaVersionNumber(1): upcast_while_the_application_writes
            }
        },
    )

    report = upgrades.upgrade_collection(request())

    assert (report.upgraded, report.changed_meanwhile) == (
        DocumentCount(0),
        DocumentCount(1),
    )
    assert read_stored(connection_pool, key)["title"] == "Written by the application"


def test_real_collections_upgrade_with_nothing_to_do(
    connection_pool: PostgresConnectionPoolClient,
) -> None:
    upgrades = PostgresStoredDocumentUpgradeAdapter(connection_pool)

    report = upgrades.upgrade_collection(
        CollectionUpgradeRequest(collection_name=DocumentCollectionName("bookings"))
    )

    assert report.outdated == DocumentCount(0)
    with pytest.raises(NotFoundError):
        upgrades.upgrade_collection(
            CollectionUpgradeRequest(collection_name=DocumentCollectionName("nope"))
        )


def test_unversioned_documents_count_as_the_first_version(
    connection_pool: PostgresConnectionPoolClient,
) -> None:
    upgrades = PostgresStoredDocumentUpgradeAdapter(
        connection_pool,
        collections=[
            DocumentCollectionDefinition(NOTES_COLLECTION, ExamplePersistentDocument)
        ],
    )

    report = upgrades.upgrade_collection(request())

    assert report.current_version == DocumentSchemaVersionNumber(1)
    assert report.outdated == DocumentCount(0)
    with pytest.raises(TypeError):
        read_position(("key", "{}", None, 1))
