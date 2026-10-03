"""One entry of the collection catalog: a stored document type and its table."""

from dataclasses import dataclass

from base_pydantic_schemas import PersistentDocument

from app.schemas.typings.storage.constrained_strings import DocumentCollectionName


@dataclass(frozen=True)
class DocumentCollectionDefinition:
    """A stored document type and the name of its collection."""

    name: DocumentCollectionName
    document_type: type[PersistentDocument]
