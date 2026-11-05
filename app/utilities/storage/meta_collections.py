"""
The catalog entry of Meta's self-serve connection (1212): the Facebook
sign-ins owners start on the Channels page. Part of DOCUMENT_COLLECTIONS
(document_collection_catalog.py).
"""

from app.schemas.domain.meta_connections import MetaConnectionStateDocument
from app.schemas.typings.storage.constrained_strings import DocumentCollectionName
from app.utilities.storage.document_collection_definition import (
    DocumentCollectionDefinition,
)

META_CONNECTION_COLLECTIONS: tuple[DocumentCollectionDefinition, ...] = (
    DocumentCollectionDefinition(
        DocumentCollectionName("meta_connection_states"),
        MetaConnectionStateDocument,
    ),
)
