"""
The catalog entries of what the assistant is worth to a business: the
average check, each owner's digest choices, the stored digests and monthly
reports (1061), and what customers ask about, grouped every night (1100).
Part of DOCUMENT_COLLECTIONS (document_collection_catalog.py).
"""

from app.schemas.domain.conversation_topics import ConversationTopicsDocument
from app.schemas.domain.value_reports import ValueReportDocument
from app.schemas.domain.value_settings import (
    DigestPreferencesDocument,
    ValueSettingsDocument,
)
from app.schemas.typings.storage.constrained_strings import DocumentCollectionName
from app.utilities.storage.document_collection_definition import (
    DocumentCollectionDefinition,
)

VALUE_COLLECTIONS: tuple[DocumentCollectionDefinition, ...] = (
    DocumentCollectionDefinition(
        DocumentCollectionName("value_settings"), ValueSettingsDocument
    ),
    DocumentCollectionDefinition(
        DocumentCollectionName("digest_preferences"), DigestPreferencesDocument
    ),
    DocumentCollectionDefinition(
        DocumentCollectionName("value_reports"), ValueReportDocument
    ),
    DocumentCollectionDefinition(
        DocumentCollectionName("conversation_topics"), ConversationTopicsDocument
    ),
)
