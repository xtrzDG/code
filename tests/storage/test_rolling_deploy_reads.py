"""
Two releases on one Postgres table, as during a rolling deploy or after a
rollback: each reads what the other wrote.
"""

from typing import cast

import pytest

from app.adapters.storage.document_upgrades import StoredJsonObject
from app.adapters.storage.persisted_document_codec import parse_stored_object
from app.clients.postgres.postgres_connection_pool_client import (
    PostgresConnectionPoolClient,
)
from app.schemas.domain.knowledge import KnowledgeItemDocument
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.knowledge.strings import KnowledgeTitle
from tests.storage.builders import COUNTRY_SAMPLES, build_knowledge_item
from tests.storage.conftest import PostgresCollectionFactory
from tests.storage.evolution_documents import (
    NOTES_TABLE,
    NoteV1,
    NoteV2,
    build_note_v2,
)
from tests.storage.stored_rows import read_stored, write_stored

# Seeding and checking rows of several businesses runs platform-wide; the
# business scopes a test enters nest inside (tests/storage/conftest.py).
pytestmark = pytest.mark.usefixtures("platform_scope")


def test_the_previous_release_reads_and_rewrites_rows_of_the_next_one(
    postgres_collections: PostgresCollectionFactory,
    connection_pool: PostgresConnectionPoolClient,
) -> None:
    next_release = postgres_collections(NoteV2, NOTES_TABLE)
    previous_release = postgres_collections(NoteV1, NOTES_TABLE)
    note = build_note_v2(BusinessId())
    key = str(note.id)

    next_release.upsert(key, note)
    assert read_stored(connection_pool, key)["schema_version"] == "2"

    seen_by_previous = previous_release.get(key)
    assert seen_by_previous is not None
    assert seen_by_previous.title == note.title
    assert previous_release.list_all() == [seen_by_previous]

    def rename(stored: NoteV1) -> NoteV1:
        stored.title = KnowledgeTitle("Renamed by the old release")
        return stored

    assert previous_release.modify(key, rename) is not None
    # The old release writes its own shape: the new fields are gone and the
    # row says so, so the next release reads it as an older document.
    rewritten = read_stored(connection_pool, key)
    assert rewritten["schema_version"] == "1"
    assert "pin_order" not in rewritten

    seen_by_next = next_release.get(key)
    assert seen_by_next is not None
    assert seen_by_next.title == KnowledgeTitle("Renamed by the old release")
    assert seen_by_next.pin_order is None
    assert str(seen_by_next.schema_version) == "2"


def test_a_real_document_with_fields_of_a_future_release_still_loads(
    postgres_collections: PostgresCollectionFactory,
    connection_pool: PostgresConnectionPoolClient,
) -> None:
    item = build_knowledge_item(COUNTRY_SAMPLES[0], BusinessId())
    future: StoredJsonObject = parse_stored_object(item.model_dump_json())
    future["schema_version"] = "2"
    future["added_by_the_next_release"] = {"anything": [1, "two"]}
    attributes = future["attributes"]
    assert isinstance(attributes, list) and attributes
    for attribute in cast(list[object], attributes):
        assert isinstance(attribute, dict)
        attribute["shown_in_widget"] = True
    write_stored(connection_pool, str(item.id), item.business_id, future)

    items = postgres_collections(KnowledgeItemDocument, NOTES_TABLE)

    assert items.get(str(item.id)) == item
