"""
The catalog entry of the idempotency keys of creating requests (1174): a
platform collection (a key belongs to a user, and POST /v1/assistants
creates the business it is for). Part of DOCUMENT_COLLECTIONS
(document_collection_catalog.py).
"""

from app.schemas.domain.idempotency_keys import IdempotencyKeyDocument
from app.schemas.typings.storage.constrained_strings import DocumentCollectionName
from app.utilities.storage.document_collection_definition import (
    DocumentCollectionDefinition,
)

IDEMPOTENCY_COLLECTIONS: tuple[DocumentCollectionDefinition, ...] = (
    DocumentCollectionDefinition(
        DocumentCollectionName("idempotency_keys"), IdempotencyKeyDocument
    ),
)
