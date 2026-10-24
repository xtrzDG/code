"""One entry of the collection catalog: a stored document type and its table."""

from dataclasses import dataclass

from base_pydantic_schemas import PersistentDocument

from app.schemas.typings.storage.constrained_strings import DocumentCollectionName


@dataclass(frozen=True)
class DocumentCollectionDefinition:
    """
    A stored document type and the name of its collection.

    An append-only collection (the audit log, migration 1193) is never
    rewritten: its old rows keep the shape they were written in and read
    through their upcasters, so no document migration touches them.
    """

    name: DocumentCollectionName
    document_type: type[PersistentDocument]
    is_append_only: bool = False
