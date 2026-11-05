"""
The catalog entries of Customers (1140): the owner's saved segments and
the team's customer settings (business collections). Part of
DOCUMENT_COLLECTIONS (document_collection_catalog.py); their documents are
read by business and id only, so they declare no lookup fields of their
own. The contacts' card lookups (tags, VIP, blocked) are with the other
contact fields in document_lookup_catalog.py.
"""

from app.schemas.domain.customer_segments import CustomerSegmentDocument
from app.schemas.domain.customer_settings import CustomerSettingsDocument
from app.schemas.typings.storage.constrained_strings import DocumentCollectionName
from app.utilities.storage.document_collection_definition import (
    DocumentCollectionDefinition,
)

CUSTOMER_SEGMENTS: DocumentCollectionName = DocumentCollectionName("customer_segments")
CUSTOMER_SETTINGS: DocumentCollectionName = DocumentCollectionName("customer_settings")
CUSTOMER_COLLECTIONS: tuple[DocumentCollectionDefinition, ...] = (
    DocumentCollectionDefinition(CUSTOMER_SEGMENTS, CustomerSegmentDocument),
    DocumentCollectionDefinition(CUSTOMER_SETTINGS, CustomerSettingsDocument),
)
