"""
One stored document type as three consecutive releases wrote it.

- `NoteV1`: the old release (N - 1).
- `NoteV2`: the next release (N) expands the shape: a new optional field,
  a new optional field of a nested object. No upcaster needed.
- `NoteV3`: the release after (N + 1) renames `title` to `heading`, which
  needs an upcaster from version 2 (`upgrade_notes_from_v2`).

They are stored in the `knowledge_items` table, which has no generated
lookup columns besides `business_id`.
"""

from base_pydantic_schemas import BaseDocument, PersistentDocument, SchemaVersion
from pydantic import Field

from app.adapters.storage.document_upgrades import DocumentUpcaster, StoredJsonObject
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.integers import ExampleInt
from app.schemas.typings.knowledge.constrained_strings import KnowledgeAttributeKey
from app.schemas.typings.knowledge.prefixed_id import KnowledgeItemId
from app.schemas.typings.knowledge.strings import (
    KnowledgeAttributeValue,
    KnowledgeTitle,
)
from app.schemas.typings.storage.constrained_integers import (
    DocumentSchemaVersionNumber,
)
from app.schemas.typings.storage.constrained_strings import DocumentCollectionName

NOTES_TABLE: str = "knowledge_items"
NOTES_COLLECTION: DocumentCollectionName = DocumentCollectionName(NOTES_TABLE)


class NoteLabelV1(PersistentDocument):
    key: KnowledgeAttributeKey


class NoteV1(BaseDocument):
    id: KnowledgeItemId = Field(default_factory=KnowledgeItemId)
    business_id: BusinessId
    title: KnowledgeTitle
    labels: list[NoteLabelV1] = Field(default_factory=list[NoteLabelV1])


class NoteV1Changed(BaseDocument):
    """NoteV1 with a new field but without a version bump (refused)."""

    id: KnowledgeItemId = Field(default_factory=KnowledgeItemId)
    business_id: BusinessId
    title: KnowledgeTitle
    labels: list[NoteLabelV1] = Field(default_factory=list[NoteLabelV1])
    pin_order: ExampleInt | None = None


class NoteV1Described(BaseDocument):
    """NoteV1 with only prose changed: the same stored shape."""

    id: KnowledgeItemId = Field(
        default_factory=KnowledgeItemId, description="The note's id."
    )
    business_id: BusinessId
    title: KnowledgeTitle = Field(description="What the note is about.")
    labels: list[NoteLabelV1] = Field(default_factory=list[NoteLabelV1])


class NoteLabelV2(PersistentDocument):
    key: KnowledgeAttributeKey
    caption: KnowledgeAttributeValue | None = None


class NoteV2(BaseDocument):
    schema_version: SchemaVersion = SchemaVersion("2")
    id: KnowledgeItemId = Field(default_factory=KnowledgeItemId)
    business_id: BusinessId
    title: KnowledgeTitle
    labels: list[NoteLabelV2] = Field(default_factory=list[NoteLabelV2])
    pin_order: ExampleInt | None = None


class NoteV3(BaseDocument):
    schema_version: SchemaVersion = SchemaVersion("3")
    id: KnowledgeItemId = Field(default_factory=KnowledgeItemId)
    business_id: BusinessId
    heading: KnowledgeTitle
    labels: list[NoteLabelV2] = Field(default_factory=list[NoteLabelV2])
    pin_order: ExampleInt | None = None


def upgrade_notes_from_v2(document: StoredJsonObject) -> StoredJsonObject:
    upgraded: StoredJsonObject = dict(document)
    upgraded["heading"] = upgraded.pop("title")
    return upgraded


NOTE_UPCASTERS: dict[DocumentSchemaVersionNumber, DocumentUpcaster] = {
    DocumentSchemaVersionNumber(2): upgrade_notes_from_v2,
}


def build_note_v1(business_id: BusinessId) -> NoteV1:
    return NoteV1(
        business_id=business_id,
        title=KnowledgeTitle("Opening hours"),
        labels=[NoteLabelV1(key=KnowledgeAttributeKey("season"))],
    )


def build_note_v2(business_id: BusinessId) -> NoteV2:
    return NoteV2(
        business_id=business_id,
        title=KnowledgeTitle("Opening hours"),
        labels=[
            NoteLabelV2(
                key=KnowledgeAttributeKey("season"),
                caption=KnowledgeAttributeValue("summer"),
            )
        ],
        pin_order=ExampleInt(3),
    )
