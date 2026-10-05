"""
The catalog entries of the platform's own operations (1093, platform-wide
collections): the episodes of the platform alerts, the recorded backups
and restore drills, the incident log; the status page's announcements
and history and each person's guidance (1111). Part of DOCUMENT_COLLECTIONS
(document_collection_catalog.py).
"""

from app.schemas.domain.client_standings import ClientStandingDocument
from app.schemas.domain.help_progress import HelpProgressDocument
from app.schemas.domain.incidents import IncidentDocument
from app.schemas.domain.maintenance_runs import MaintenanceRunDocument
from app.schemas.domain.platform_alerts import PlatformAlertStateDocument
from app.schemas.domain.platform_status import (
    PlatformAnnouncementDocument,
    PlatformStatusDayDocument,
)
from app.schemas.typings.storage.constrained_strings import DocumentCollectionName
from app.utilities.storage.document_collection_definition import (
    DocumentCollectionDefinition,
)

OPERATIONS_COLLECTIONS: tuple[DocumentCollectionDefinition, ...] = (
    DocumentCollectionDefinition(
        DocumentCollectionName("platform_alert_states"), PlatformAlertStateDocument
    ),
    DocumentCollectionDefinition(
        DocumentCollectionName("maintenance_runs"), MaintenanceRunDocument
    ),
    DocumentCollectionDefinition(DocumentCollectionName("incidents"), IncidentDocument),
    # The platform admin's client list, refreshed by a periodic job (1122).
    DocumentCollectionDefinition(
        DocumentCollectionName("client_standings"), ClientStandingDocument
    ),
    # The status page, the cabinet's banner and guidance (1111).
    DocumentCollectionDefinition(
        DocumentCollectionName("platform_announcements"), PlatformAnnouncementDocument
    ),
    DocumentCollectionDefinition(
        DocumentCollectionName("platform_status_days"), PlatformStatusDayDocument
    ),
    DocumentCollectionDefinition(
        DocumentCollectionName("help_progress"), HelpProgressDocument
    ),
)
