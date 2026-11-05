"""
The catalog entry of the consent ledger (1246), with the campaigns' entries
(growth_collections.py) part of DOCUMENT_COLLECTIONS
(document_collection_catalog.py) and DOCUMENT_LOOKUP_FIELDS
(document_lookup_catalog.py).

- consent_records: append-only (the database refuses changes, 1246); a
  customer's entries, oldest first (`contact_id`, `created_at`).
"""

from collections.abc import Mapping

from app.schemas.domain.consent_records import ConsentRecordDocument
from app.schemas.dto.storage_queries import DocumentLookupField
from app.schemas.typings.storage.constrained_strings import DocumentCollectionName
from app.utilities.storage.document_collection_definition import (
    DocumentCollectionDefinition,
)
from app.utilities.storage.lookup_field_builders import integer_field, text_field

CONSENT_RECORDS: DocumentCollectionName = DocumentCollectionName("consent_records")

CONSENT_COLLECTIONS: tuple[DocumentCollectionDefinition, ...] = (
    DocumentCollectionDefinition(
        CONSENT_RECORDS, ConsentRecordDocument, is_append_only=True
    ),
)

CONSENT_LOOKUP_FIELDS: Mapping[
    DocumentCollectionName, tuple[DocumentLookupField, ...]
] = {CONSENT_RECORDS: (text_field("contact_id"), integer_field("created_at"))}
