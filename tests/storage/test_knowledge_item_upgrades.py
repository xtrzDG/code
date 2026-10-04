"""Version 1 knowledge items whose duration no booking can last still read."""

import json

import pytest

from app.adapters.storage.document_upgrades import (
    CURRENT_SCHEMA_VERSION,
    StoredJsonObject,
    upcasters_of,
    upgrade_stored_json,
)
from app.adapters.storage.knowledge_item_upgrades import (
    upgrade_knowledge_items_from_v1,
)
from app.schemas.domain.knowledge import KnowledgeItemDocument
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.storage.constrained_strings import DocumentCollectionName

KNOWLEDGE_ITEMS = DocumentCollectionName("knowledge_items")


def stored_v1(
    duration: object, attributes: list[object] | None = None
) -> StoredJsonObject:
    document: StoredJsonObject = {
        "schema_version": "1",
        "business_id": str(BusinessId()),
        "kind": "room_type",
        "title": "Deluxe room",
        "duration_minutes": duration,
    }
    if attributes is not None:
        document["attributes"] = attributes

    return document


def read(document: StoredJsonObject) -> KnowledgeItemDocument:
    upgraded = upgrade_stored_json(
        document,
        upcasters_of(KNOWLEDGE_ITEMS),
        CURRENT_SCHEMA_VERSION[KNOWLEDGE_ITEMS],
    )
    return KnowledgeItemDocument.model_validate_json(json.dumps(upgraded))


def test_a_day_long_duration_moves_to_an_attribute() -> None:
    item = read(stored_v1(1440))

    assert item.duration_minutes is None
    assert [(attribute.key, attribute.value) for attribute in item.attributes] == [
        ("duration_minutes", "1440")
    ]
    assert item.schema_version == "3"


@pytest.mark.parametrize("duration", [5, 45, 720, None])
def test_a_bookable_duration_stays_as_it_is(duration: int | None) -> None:
    item = read(stored_v1(duration))

    assert item.duration_minutes == duration
    assert item.attributes == []


def test_a_too_short_duration_moves_too_and_keeps_other_attributes() -> None:
    upgraded = upgrade_knowledge_items_from_v1(
        stored_v1(2, [{"key": "floor", "value": "2"}])
    )

    assert upgraded["duration_minutes"] is None
    assert upgraded["attributes"] == [
        {"key": "floor", "value": "2"},
        {"key": "duration_minutes", "value": "2"},
    ]


def test_an_existing_duration_attribute_is_not_repeated() -> None:
    original = stored_v1(2000, [{"key": "duration_minutes", "value": "2 days"}])

    upgraded = upgrade_knowledge_items_from_v1(original)

    assert upgraded["attributes"] == [{"key": "duration_minutes", "value": "2 days"}]
    assert original["duration_minutes"] == 2000


@pytest.mark.parametrize("duration", [True, "1440", 12.5])
def test_values_that_are_not_whole_minutes_are_left_to_validation(
    duration: object,
) -> None:
    original = stored_v1(duration)

    assert upgrade_knowledge_items_from_v1(original) is original
