"""
The collection of the owners' answers to the second-factor reminder
(migration 1201), a part of the collection catalog
(`document_collection_catalog.py`): `security_nudges`, one document per
business and person (the id derives from both), read by that id only.
"""

from app.schemas.domain.security_nudges import SecurityNudgeDocument
from app.schemas.typings.storage.constrained_strings import DocumentCollectionName
from app.utilities.storage.document_collection_definition import (
    DocumentCollectionDefinition,
)

SECURITY_NUDGES: DocumentCollectionName = DocumentCollectionName("security_nudges")
SECURITY_NUDGE_COLLECTIONS: tuple[DocumentCollectionDefinition, ...] = (
    DocumentCollectionDefinition(SECURITY_NUDGES, SecurityNudgeDocument),
)
