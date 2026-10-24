"""
The catalog entries of rented phone numbers (1213). Part of
DOCUMENT_COLLECTIONS (document_collection_catalog.py) and
DOCUMENT_LOOKUP_FIELDS (document_lookup_catalog.py).

- phone_numbers: the numbers rented for a business, read within it by the
  business's own column; across businesses by `status` for the jobs that
  return given-up numbers, keep the voice agent attached and bill rental
  months (`billed_until`), and by `phone_number` to refuse a number that is
  already someone's;
- phone_number_requests: one per business, read by id; open ones across
  businesses by `status` (the maintenance job closes a request once the
  business's phone channel is connected).
"""

from collections.abc import Mapping

from app.schemas.domain.phone_numbers import (
    PhoneNumberDocument,
    PhoneNumberRequestDocument,
)
from app.schemas.dto.storage_queries import DocumentLookupField
from app.schemas.typings.storage.constrained_strings import DocumentCollectionName
from app.utilities.storage.document_collection_definition import (
    DocumentCollectionDefinition,
)
from app.utilities.storage.lookup_field_builders import integer_field, text_field

PHONE_NUMBERS: DocumentCollectionName = DocumentCollectionName("phone_numbers")
PHONE_NUMBER_REQUESTS: DocumentCollectionName = DocumentCollectionName(
    "phone_number_requests"
)

PHONE_NUMBER_COLLECTIONS: tuple[DocumentCollectionDefinition, ...] = (
    DocumentCollectionDefinition(PHONE_NUMBERS, PhoneNumberDocument),
    DocumentCollectionDefinition(PHONE_NUMBER_REQUESTS, PhoneNumberRequestDocument),
)

PHONE_NUMBER_LOOKUP_FIELDS: Mapping[
    DocumentCollectionName, tuple[DocumentLookupField, ...]
] = {
    PHONE_NUMBERS: (
        text_field("status"),
        text_field("phone_number"),
        integer_field("billed_until"),
    ),
    PHONE_NUMBER_REQUESTS: (text_field("status"),),
}
