"""
The catalog entries of platform access (1103): the platform admins and
their roles (a platform collection), and platform support's time-boxed
access to each business (a business collection). Part of
DOCUMENT_COLLECTIONS (document_collection_catalog.py).
"""

from app.schemas.domain.platform_admins import PlatformAdminDocument
from app.schemas.domain.support_access_grants import SupportAccessGrantDocument
from app.schemas.typings.storage.constrained_strings import DocumentCollectionName
from app.utilities.storage.document_collection_definition import (
    DocumentCollectionDefinition,
)

ACCESS_COLLECTIONS: tuple[DocumentCollectionDefinition, ...] = (
    DocumentCollectionDefinition(
        DocumentCollectionName("platform_admins"), PlatformAdminDocument
    ),
    DocumentCollectionDefinition(
        DocumentCollectionName("support_access_grants"), SupportAccessGrantDocument
    ),
)
