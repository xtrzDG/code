"""
The catalog entries of data-subject rights (1113): each business's
suppression list (the customers who said STOP, kept through erasure) and
the full exports of a business's data, with their one-time download
links (1134); and of retention (1123): each
business's privacy settings and how far its retention purge got. Part of
DOCUMENT_COLLECTIONS (document_collection_catalog.py).
"""

from app.schemas.domain.business_exports import (
    BusinessExportDocument,
    ExportDownloadLinkDocument,
)
from app.schemas.domain.business_privacy_settings import (
    BusinessPrivacySettingsDocument,
)
from app.schemas.domain.retention_purges import RetentionPurgeStateDocument
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
    DocumentCollectionDefinition(
        DocumentCollectionName("export_download_links"),
        ExportDownloadLinkDocument,
    ),
    DocumentCollectionDefinition(
        DocumentCollectionName("business_privacy_settings"),
        BusinessPrivacySettingsDocument,
    ),
    DocumentCollectionDefinition(
        DocumentCollectionName("retention_purge_states"),
        RetentionPurgeStateDocument,
    ),
)
