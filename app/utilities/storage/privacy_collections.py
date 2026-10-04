"""
The catalog entries of data-subject rights (1113): each business's
suppression list (the customers who said STOP, kept through erasure) and
the full exports of a business's data. Part of DOCUMENT_COLLECTIONS
(document_collection_catalog.py).
"""

from app.schemas.domain.business_exports import BusinessExportDocument
from app.schemas.domain.suppression import SuppressionEntryDocument
from app.schemas.typings.storage.constrained_strings import DocumentCollectionName
from app.utilities.storage.document_collection_definition import (
    DocumentCollectionDefinition,
)

PRIVACY_COLLECTIONS: tuple[DocumentCollectionDefinition, ...] = (
    DocumentCollectionDefinition(
        DocumentCollectionName("suppression_entries"), SuppressionEntryDocument
    ),
    DocumentCollectionDefinition(
        DocumentCollectionName("business_exports"), BusinessExportDocument
    ),
)
