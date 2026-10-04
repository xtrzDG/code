"""
The catalog entries of the platform's own operations (1093, platform-wide
collections): the episodes of the platform alerts, the recorded backups
and restore drills, and the incident log. Part of DOCUMENT_COLLECTIONS
(document_collection_catalog.py).
"""

from app.schemas.domain.incidents import IncidentDocument
from app.schemas.domain.maintenance_runs import MaintenanceRunDocument
from app.schemas.domain.platform_alerts import PlatformAlertStateDocument
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
)
