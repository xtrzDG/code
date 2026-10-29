"""
The catalog entries of customer memory (1121): how the assistant of each
business treats returning customers (a business collection, one document
per business, read by its derived id: no lookup column). Part of
DOCUMENT_COLLECTIONS (document_collection_catalog.py).
"""

from app.schemas.domain.assistant_settings import AssistantSettingsDocument
from app.schemas.typings.storage.constrained_strings import DocumentCollectionName
from app.utilities.storage.document_collection_definition import (
    DocumentCollectionDefinition,
)

MEMORY_COLLECTIONS: tuple[DocumentCollectionDefinition, ...] = (
    DocumentCollectionDefinition(
        DocumentCollectionName("assistant_settings"), AssistantSettingsDocument
    ),
)
