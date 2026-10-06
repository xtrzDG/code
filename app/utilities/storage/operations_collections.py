"""
The catalog entries of the platform's own operations (1093, platform-wide
collections): the episodes of the platform alerts, the recorded backups
and restore drills, the incident log; the status page's announcements
and history and each person's guidance (1111); the service level
indicators in five-minute slots and hourly rows (1163); the post-deploy
data tasks' state (1164); the marks of the platform's watchers
(1173). Part of DOCUMENT_COLLECTIONS
(document_collection_catalog.py).
"""

from app.schemas.domain.client_standings import ClientStandingDocument
from app.schemas.domain.data_tasks import DataTaskStateDocument
from app.schemas.domain.help_progress import HelpProgressDocument
from app.schemas.domain.incidents import IncidentDocument
from app.schemas.domain.maintenance_runs import MaintenanceRunDocument
from app.schemas.domain.platform_alerts import PlatformAlertStateDocument
from app.schemas.domain.platform_monitors import PlatformMonitorDocument
from app.schemas.domain.platform_status import (
    PlatformAnnouncementDocument,
    PlatformStatusDayDocument,
)
from app.schemas.domain.service_levels import (
    ServiceLevelHourDocument,
    ServiceLevelSlotDocument,
)
from app.schemas.typings.storage.constrained_strings import DocumentCollectionName
from app.utilities.storage.document_collection_definition import (
    DocumentCollectionDefinition,
)

DATA_TASK_STATES_COLLECTION: DocumentCollectionName = DocumentCollectionName(
    "data_task_states"
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
    # The post-deploy data tasks, one state per registry key (1164).
    DocumentCollectionDefinition(DATA_TASK_STATES_COLLECTION, DataTaskStateDocument),
    # The SLIs: five-minute slots per series, one row per hour (1163).
    DocumentCollectionDefinition(
        DocumentCollectionName("service_level_slots"), ServiceLevelSlotDocument
    ),
    DocumentCollectionDefinition(
        DocumentCollectionName("service_level_hours"), ServiceLevelHourDocument
    ),
    # When each watcher of the platform last looked; the watchdog's lease.
    DocumentCollectionDefinition(
        DocumentCollectionName("platform_monitors"), PlatformMonitorDocument
    ),
)
