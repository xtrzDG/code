"""
The catalog entries of invoicing (1114): each business's billing details
(a business collection) and the yearly invoice counters of the seller (a
platform collection). Part of DOCUMENT_COLLECTIONS
(document_collection_catalog.py).
"""

from app.schemas.domain.billing_profiles import (
    BillingProfileDocument,
    InvoiceCounterDocument,
)
from app.schemas.typings.storage.constrained_strings import DocumentCollectionName
from app.utilities.storage.document_collection_definition import (
    DocumentCollectionDefinition,
)

INVOICING_COLLECTIONS: tuple[DocumentCollectionDefinition, ...] = (
    DocumentCollectionDefinition(
        DocumentCollectionName("billing_profiles"), BillingProfileDocument
    ),
    DocumentCollectionDefinition(
        DocumentCollectionName("invoice_counters"), InvoiceCounterDocument
    ),
)
