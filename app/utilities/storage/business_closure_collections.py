"""
The catalog entries of closing and deleting a business (1220). Part of
DOCUMENT_COLLECTIONS (document_collection_catalog.py) and
DOCUMENT_LOOKUP_FIELDS (document_lookup_catalog.py).

- business_closures (business collection): one per business, read by id;
  across businesses by `delete_after` for the hourly sweep that queues the
  deletions that are due;
- business_deletions (platform collection, the deletion ledger): read by
  id (derived from the business: the deletion job, the certificate); a
  person's entries by `owners[].user_id` (Account → the certificates of
  their closed businesses).
"""

from collections.abc import Mapping

from app.schemas.domain.business_closures import (
    BusinessClosureDocument,
    BusinessDeletionDocument,
)
from app.schemas.dto.storage_queries import DocumentLookupField
from app.schemas.typings.storage.constrained_strings import DocumentCollectionName
from app.utilities.storage.document_collection_definition import (
    DocumentCollectionDefinition,
)
from app.utilities.storage.lookup_field_builders import element_field, integer_field

BUSINESS_CLOSURES: DocumentCollectionName = DocumentCollectionName("business_closures")
BUSINESS_DELETIONS: DocumentCollectionName = DocumentCollectionName(
    "business_deletions"
)

BUSINESS_CLOSURE_COLLECTIONS: tuple[DocumentCollectionDefinition, ...] = (
    DocumentCollectionDefinition(BUSINESS_CLOSURES, BusinessClosureDocument),
    DocumentCollectionDefinition(BUSINESS_DELETIONS, BusinessDeletionDocument),
)

BUSINESS_CLOSURE_LOOKUP_FIELDS: Mapping[
    DocumentCollectionName, tuple[DocumentLookupField, ...]
] = {
    BUSINESS_CLOSURES: (integer_field("delete_after"),),
    BUSINESS_DELETIONS: (
        element_field("owners[].user_id"),
        integer_field("started_at"),
    ),
}
