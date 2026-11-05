"""
The collections of the sub-processor change notices (migration 1124), a
part of the collection catalog (`document_collection_catalog.py`):

- `subprocessor_notices`: the notice each business got about each change
  of the sub-processor list, once per business and change (the id derives
  from both);
- `subprocessor_announcements`: each change's announcement to the platform
  (a platform collection), once per change.
"""

from app.schemas.domain.legal import (
    SubprocessorAnnouncementDocument,
    SubprocessorNoticeDocument,
)
from app.schemas.typings.storage.constrained_strings import DocumentCollectionName
from app.utilities.storage.document_collection_definition import (
    DocumentCollectionDefinition,
)

SUBPROCESSOR_NOTICES_COLLECTION: DocumentCollectionName = DocumentCollectionName(
    "subprocessor_notices"
)
SUBPROCESSOR_ANNOUNCEMENTS_COLLECTION: DocumentCollectionName = DocumentCollectionName(
    "subprocessor_announcements"
)
LEGAL_COLLECTIONS: tuple[DocumentCollectionDefinition, ...] = (
    DocumentCollectionDefinition(
        SUBPROCESSOR_NOTICES_COLLECTION, SubprocessorNoticeDocument
    ),
    DocumentCollectionDefinition(
        SUBPROCESSOR_ANNOUNCEMENTS_COLLECTION, SubprocessorAnnouncementDocument
    ),
)
