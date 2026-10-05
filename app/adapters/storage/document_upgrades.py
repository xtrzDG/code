"""
Schema versions of stored documents and the upcasters between them.

Every stored document carries `schema_version` ("1", "2", ...). The current
version of a collection is the `schema_version` default of its document
type (`BaseDocument` starts at "1"); a release that changes the stored shape
bumps it on the model:

    class BookingDocument(BaseDocument):
        schema_version: SchemaVersion = SchemaVersion("2")

Documents are always written with the writer's current version
(`PersistedDocumentCodec.encode`). On read, a document of an older version
runs through the upcasters of its collection, one version step at a time,
before it is validated; one of a newer version (written by the next release
during a rolling deploy, or before a rollback) is read as it is, its unknown
fields ignored.

An upcaster turns the raw JSON of version N into that of version N + 1. It
is needed when old data is not valid, or not correct, for the new model: a
renamed or removed field, a new required field, a changed value. Adding an
optional field with a default needs only the version bump. Register it under
the version it upgrades from:

    def upgrade_bookings_from_v1(document: StoredJsonObject) -> StoredJsonObject:
        upgraded = dict(document)
        upgraded["party_size"] = upgraded.pop("guests", 1)
        return upgraded

    DOCUMENT_UPCASTERS = {
        DocumentCollectionName("bookings"): {
            DocumentSchemaVersionNumber(1): upgrade_bookings_from_v1,
        },
    }

Upcasters are pure functions of stored JSON (the storage boundary, before
validation), never delete data the old release still reads, and stay in the
code as long as rows of the old version may exist (`workshop
migrate-documents` rewrites them). Rules for changing a stored shape:
docs/operations/deploys.md; the golden fixtures and schema snapshots that
enforce them: tests/architecture_policy/test_document_evolution.py.
"""

from collections.abc import Callable, Mapping

from base_pydantic_schemas import PersistentDocument, SchemaVersion
from pydantic.fields import FieldInfo

from app.adapters.storage.channel_upgrades import upgrade_channels_from_v3
from app.adapters.storage.contact_upgrades import upgrade_contacts_from_v2
from app.adapters.storage.knowledge_item_upgrades import (
    upgrade_knowledge_items_from_v1,
)
from app.adapters.storage.topic_upgrades import upgrade_conversation_topics_from_v1
from app.schemas.exceptions.storage_errors import UnreadableStoredDocumentError
from app.schemas.typings.storage.constrained_integers import (
    DocumentSchemaVersionNumber,
)
from app.schemas.typings.storage.constrained_strings import DocumentCollectionName
from app.utilities.storage.document_collection_catalog import DOCUMENT_COLLECTIONS

SCHEMA_VERSION_FIELD_NAME: str = "schema_version"
# Rows written before documents had a version (none in production) and
# documents without the field read as the first version.
FIRST_SCHEMA_VERSION: DocumentSchemaVersionNumber = DocumentSchemaVersionNumber(1)

# Stored JSON of one document, before validation (the storage boundary).
type StoredJsonObject = dict[str, object]
type DocumentUpcaster = Callable[[StoredJsonObject], StoredJsonObject]

DOCUMENT_UPCASTERS: Mapping[
    DocumentCollectionName,
    Mapping[DocumentSchemaVersionNumber, DocumentUpcaster],
] = {
    DocumentCollectionName("channels"): {
        DocumentSchemaVersionNumber(3): upgrade_channels_from_v3,
    },
    DocumentCollectionName("contacts"): {
        DocumentSchemaVersionNumber(2): upgrade_contacts_from_v2,
    },
    DocumentCollectionName("conversation_topics"): {
        DocumentSchemaVersionNumber(1): upgrade_conversation_topics_from_v1,
    },
    DocumentCollectionName("knowledge_items"): {
        DocumentSchemaVersionNumber(1): upgrade_knowledge_items_from_v1,
    },
}
NO_UPCASTERS: Mapping[DocumentSchemaVersionNumber, DocumentUpcaster] = {}


def declared_schema_version(
    document_type: type[PersistentDocument],
) -> DocumentSchemaVersionNumber | None:
    """
    The current version of a document type: its `schema_version` default.

    None for a type without the field (a `PersistentDocument` that is not a
    `BaseDocument`): such documents are read tolerantly but never upcast.
    """

    field: FieldInfo | None = document_type.model_fields.get(SCHEMA_VERSION_FIELD_NAME)
    if field is None:
        return None

    return parse_schema_version(field.default)


def upcasters_of(
    collection_name: DocumentCollectionName | None,
) -> Mapping[DocumentSchemaVersionNumber, DocumentUpcaster]:
    """The upcasters of a collection by the version they upgrade from."""

    if collection_name is None:
        return NO_UPCASTERS

    return DOCUMENT_UPCASTERS.get(collection_name, NO_UPCASTERS)


def stored_schema_version(document: StoredJsonObject) -> DocumentSchemaVersionNumber:
    """The version a stored document was written with."""

    if SCHEMA_VERSION_FIELD_NAME not in document:
        return FIRST_SCHEMA_VERSION

    return parse_schema_version(document[SCHEMA_VERSION_FIELD_NAME])


def parse_schema_version(value: object) -> DocumentSchemaVersionNumber:
    """UnreadableStoredDocumentError unless `value` is "1", "2", ..."""

    if not isinstance(value, str) or not (value.isascii() and value.isdecimal()):
        raise UnreadableStoredDocumentError(
            f"schema_version must be a whole number as text, got {value!r}."
        )

    text: str = str(value)
    version: int = int(text)
    if version < int(FIRST_SCHEMA_VERSION) or str(version) != text:
        raise UnreadableStoredDocumentError(
            f"schema_version must be 1 or more without leading zeros, got {text!r}."
        )

    return DocumentSchemaVersionNumber(version)


def upgrade_stored_json(
    document: StoredJsonObject,
    upcasters: Mapping[DocumentSchemaVersionNumber, DocumentUpcaster],
    current_version: DocumentSchemaVersionNumber,
) -> StoredJsonObject:
    """
    The document in the shape of `current_version`, its version stamped.

    Older documents run through every registered upcaster from their version
    up (a version without an upcaster changed nothing old data needs); newer
    ones are returned as they are, for a tolerant read. The input is never
    modified.
    """

    version: int = int(stored_schema_version(document))
    upgraded: StoredJsonObject = dict(document)
    while version < int(current_version):
        upcaster: DocumentUpcaster | None = upcasters.get(
            DocumentSchemaVersionNumber(version)
        )
        if upcaster is not None:
            upgraded = upcaster(upgraded)

        version += 1

    upgraded[SCHEMA_VERSION_FIELD_NAME] = str(schema_version_text(current_version))
    return upgraded


def schema_version_text(version: DocumentSchemaVersionNumber) -> SchemaVersion:
    """The stored form of a version number: "1", "2", ..."""

    return SchemaVersion(str(int(version)))


def build_current_schema_versions() -> dict[
    DocumentCollectionName, DocumentSchemaVersionNumber
]:
    """The current version of every catalog collection (first when undeclared)."""

    versions: dict[DocumentCollectionName, DocumentSchemaVersionNumber] = {}
    for definition in DOCUMENT_COLLECTIONS:
        declared: DocumentSchemaVersionNumber | None = declared_schema_version(
            definition.document_type
        )
        versions[definition.name] = (
            FIRST_SCHEMA_VERSION if declared is None else declared
        )

    return versions


CURRENT_SCHEMA_VERSION: Mapping[DocumentCollectionName, DocumentSchemaVersionNumber] = (
    build_current_schema_versions()
)
