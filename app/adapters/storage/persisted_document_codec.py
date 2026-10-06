"""
How stored documents are written and read back: strict on write, tolerant
and version-aware on read.

Documents stay strict (`extra="forbid"`, strict types) wherever they are
built: inputs, DTOs, use cases, and every write, which serializes a
validated document. Only this read path relaxes one rule: fields the
document type does not know are ignored (`extra="ignore"`, which pydantic
applies to every nested model too). So while a rolling deploy runs the old
release next to the new one, or after a rollback, the old release reads
documents the new one wrote with a new optional field instead of failing on
every such row. Everything else (types, required fields, enum values) is
still validated.

Reads also upgrade older documents through the upcasters of their
collection (`document_upgrades.py`) and stamp the reader's current
`schema_version`; writes stamp it too, so a stored document always says
which release shape it has. A write refuses enum values of a closed
release gate (`release_gates.py`): the previous release could not read them.
"""

import json
from collections.abc import Mapping, Sequence
from typing import cast

from base_pydantic_schemas import PersistentDocument, SchemaVersion
from pydantic import ValidationError

from app.adapters.storage.document_upgrades import (
    SCHEMA_VERSION_FIELD_NAME,
    DocumentUpcaster,
    StoredJsonObject,
    declared_schema_version,
    schema_version_text,
    stored_schema_version,
    upcasters_of,
    upgrade_stored_json,
)
from app.schemas.constants.storage import StoredDocumentVersionState
from app.schemas.dto.release_gates import ReleaseGate
from app.schemas.exceptions.storage_errors import UnreadableStoredDocumentError
from app.schemas.typings.storage.constrained_integers import (
    DocumentSchemaVersionNumber,
)
from app.schemas.typings.storage.constrained_strings import DocumentCollectionName
from app.utilities.storage.release_gates import (
    RELEASE_GATES,
    ClosedGate,
    closed_gates_of,
    refuse_closed_values,
)


class PersistedDocumentCodec[StoredDocument: PersistentDocument]:
    """
    Serializes one collection's documents and reads them back.

    `collection_name` selects the registered upcasters (None, or a name
    outside the catalog, has none) unless `upcasters` are given; the current
    version comes from the document type.
    """

    def __init__(
        self,
        document_type: type[StoredDocument],
        collection_name: DocumentCollectionName | None,
        upcasters: Mapping[DocumentSchemaVersionNumber, DocumentUpcaster] | None = None,
        release_gates: Sequence[ReleaseGate] = RELEASE_GATES,
    ) -> None:
        self._document_type: type[StoredDocument] = document_type
        self._current_version: DocumentSchemaVersionNumber | None = (
            declared_schema_version(document_type)
        )
        self._upcasters: dict[DocumentSchemaVersionNumber, DocumentUpcaster] = dict(
            upcasters_of(collection_name) if upcasters is None else upcasters
        )
        self._closed_gates: tuple[ClosedGate, ...] = closed_gates_of(
            collection_name, release_gates
        )
        # Compared with every document read: built once.
        self._current_text: SchemaVersion | None = (
            None
            if self._current_version is None
            else schema_version_text(self._current_version)
        )

    @property
    def current_version(self) -> DocumentSchemaVersionNumber | None:
        """The version this release writes; None for unversioned types."""

        return self._current_version

    def encode(self, document: StoredDocument) -> str:
        """
        JSON of the document with the current `schema_version`.

        Raises:
            ClosedReleaseGateError: it holds a value of a closed release gate.
        """

        stamped: StoredDocument = self._stamped(document)
        if self._closed_gates:
            refuse_closed_values(stamped.model_dump(mode="json"), self._closed_gates)
        return stamped.model_dump_json()

    def decode(self, stored_text: str) -> StoredDocument:
        """
        The stored document as this release's type: older versions upcast,
        unknown fields ignored, the current version stamped.
        """

        current_version: DocumentSchemaVersionNumber | None = self._current_version
        if current_version is None:
            return self._validate(stored_text)

        try:
            document: StoredDocument = self._validate(stored_text)
        except ValidationError:
            # An older shape may become valid only after its upcasters.
            return self._decode_upgraded(stored_text, current_version)

        if self._is_current(document):
            return document

        return self._decode_upgraded(stored_text, current_version)

    def version_state(self, stored_text: str) -> StoredDocumentVersionState:
        """Whether a stored document is older, newer or of this release."""

        if self._current_version is None:
            return StoredDocumentVersionState.CURRENT

        stored: int = int(stored_schema_version(parse_stored_object(stored_text)))
        if stored < int(self._current_version):
            return StoredDocumentVersionState.OLDER

        if stored > int(self._current_version):
            return StoredDocumentVersionState.NEWER

        return StoredDocumentVersionState.CURRENT

    def upgrade(self, stored_text: str) -> str:
        """The stored text rewritten in the current version's shape."""

        return self.encode(self.decode(stored_text))

    def _decode_upgraded(
        self,
        stored_text: str,
        current_version: DocumentSchemaVersionNumber,
    ) -> StoredDocument:
        upgraded: StoredJsonObject = upgrade_stored_json(
            parse_stored_object(stored_text),
            self._upcasters,
            current_version,
        )
        return self._validate(json.dumps(upgraded))

    def _validate(self, stored_text: str) -> StoredDocument:
        return self._document_type.model_validate_json(stored_text, extra="ignore")

    def _stamped(self, document: StoredDocument) -> StoredDocument:
        if self._current_text is None or self._is_current(document):
            return document

        return document.model_copy(
            update={SCHEMA_VERSION_FIELD_NAME: self._current_text}
        )

    def _is_current(self, document: PersistentDocument) -> bool:
        stored: object = getattr(document, SCHEMA_VERSION_FIELD_NAME, None)
        return stored == self._current_text


def parse_stored_object(stored_text: str) -> StoredJsonObject:
    """The stored JSON as an object; UnreadableStoredDocumentError otherwise."""

    try:
        parsed: object = json.loads(stored_text)
    except json.JSONDecodeError as error:
        raise UnreadableStoredDocumentError(
            f"A stored document is not JSON: {error.msg}."
        ) from error

    if not isinstance(parsed, dict):
        raise UnreadableStoredDocumentError(
            f"A stored document is JSON {type(parsed).__name__}, not an object."
        )

    # JSON object keys are always strings.
    return cast(StoredJsonObject, parsed)
