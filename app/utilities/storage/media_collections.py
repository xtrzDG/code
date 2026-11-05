"""
The catalog entries of the files customers send: the media of their
messages in every channel (1081) and the photos and voice notes website
chat visitors upload before their message (1191). Part of
DOCUMENT_COLLECTIONS (document_collection_catalog.py); both are read by
age for their purges (document_lookup_catalog.py).
"""

from app.schemas.domain.message_media import MessageMediaDocument
from app.schemas.domain.widget_uploads import WidgetUploadDocument
from app.schemas.typings.storage.constrained_strings import DocumentCollectionName
from app.utilities.storage.document_collection_definition import (
    DocumentCollectionDefinition,
)

MEDIA_COLLECTIONS: tuple[DocumentCollectionDefinition, ...] = (
    DocumentCollectionDefinition(
        DocumentCollectionName("message_media"), MessageMediaDocument
    ),
    DocumentCollectionDefinition(
        DocumentCollectionName("widget_uploads"), WidgetUploadDocument
    ),
)
