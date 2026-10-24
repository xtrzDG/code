"""
The catalog entries of the admin's client care (1143): the credit ledger
and the platform team's notes (business collections read per business),
the changes of a client's health (by time within a business, and by status
and time across businesses for the daily digest) and how far each digest
has looked (a platform collection read by its kind); and the steps of a
subscription's life (1161, `subscription_lifecycle_collections.py`):
cancel reasons, saves, pauses and win-back messages. Part of
DOCUMENT_COLLECTIONS (document_collection_catalog.py) and
DOCUMENT_LOOKUP_FIELDS (document_lookup_catalog.py).
"""

from collections.abc import Mapping

from app.schemas.domain.billing_credits import BillingCreditDocument
from app.schemas.domain.client_health_changes import (
    AdminDigestStateDocument,
    ClientHealthChangeDocument,
)
from app.schemas.domain.client_notes import ClientNoteDocument
from app.schemas.dto.storage_queries import DocumentLookupField
from app.schemas.typings.storage.constrained_strings import DocumentCollectionName
from app.utilities.storage.document_collection_definition import (
    DocumentCollectionDefinition,
)
from app.utilities.storage.lookup_field_builders import integer_field, text_field
from app.utilities.storage.subscription_lifecycle_collections import (
    SUBSCRIPTION_LIFECYCLE_COLLECTIONS,
    SUBSCRIPTION_LIFECYCLE_LOOKUP_FIELDS,
)

CLIENT_HEALTH_CHANGES: DocumentCollectionName = DocumentCollectionName(
    "client_health_changes"
)

CLIENT_CARE_COLLECTIONS: tuple[DocumentCollectionDefinition, ...] = (
    DocumentCollectionDefinition(
        DocumentCollectionName("billing_credits"), BillingCreditDocument
    ),
    DocumentCollectionDefinition(
        DocumentCollectionName("client_notes"), ClientNoteDocument
    ),
    DocumentCollectionDefinition(CLIENT_HEALTH_CHANGES, ClientHealthChangeDocument),
    DocumentCollectionDefinition(
        DocumentCollectionName("admin_digest_states"), AdminDigestStateDocument
    ),
    *SUBSCRIPTION_LIFECYCLE_COLLECTIONS,
)

CLIENT_CARE_LOOKUP_FIELDS: Mapping[
    DocumentCollectionName, tuple[DocumentLookupField, ...]
] = {
    CLIENT_HEALTH_CHANGES: (integer_field("changed_at"), text_field("status")),
    **SUBSCRIPTION_LIFECYCLE_LOOKUP_FIELDS,
}
