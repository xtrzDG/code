"""
The catalog entries of the platform's safety switches and watchers (1230):
part of DOCUMENT_COLLECTIONS (document_collection_catalog.py) and, through
the platform's lookup fields, DOCUMENT_LOOKUP_FIELDS. Platform collections:
they name no business (a reconciliation's mismatches name the businesses
of the orders, read only by the platform).

- platform_pauses: the global pause, one row under `platform`;
- periodic_job_heartbeats: one row per periodic job under its name; the
  missed-run alert finds the overdue ones by `due_by`;
- payment_reconciliations: one row per UTC day of the daily payment
  reconciliation, read by its day.
"""

from collections.abc import Mapping

from app.schemas.domain.payment_reconciliations import PaymentReconciliationDocument
from app.schemas.domain.periodic_job_heartbeats import PeriodicJobHeartbeatDocument
from app.schemas.domain.platform_pauses import PlatformPauseDocument
from app.schemas.dto.storage_queries import DocumentLookupField
from app.schemas.typings.storage.constrained_strings import DocumentCollectionName
from app.utilities.storage.document_collection_definition import (
    DocumentCollectionDefinition,
)
from app.utilities.storage.lookup_field_builders import integer_field

PLATFORM_PAUSES: DocumentCollectionName = DocumentCollectionName("platform_pauses")
PERIODIC_JOB_HEARTBEATS: DocumentCollectionName = DocumentCollectionName(
    "periodic_job_heartbeats"
)
PAYMENT_RECONCILIATIONS: DocumentCollectionName = DocumentCollectionName(
    "payment_reconciliations"
)

PLATFORM_SAFETY_COLLECTIONS: tuple[DocumentCollectionDefinition, ...] = (
    DocumentCollectionDefinition(PLATFORM_PAUSES, PlatformPauseDocument),
    DocumentCollectionDefinition(PERIODIC_JOB_HEARTBEATS, PeriodicJobHeartbeatDocument),
    DocumentCollectionDefinition(
        PAYMENT_RECONCILIATIONS, PaymentReconciliationDocument
    ),
)

PLATFORM_SAFETY_LOOKUP_FIELDS: Mapping[
    DocumentCollectionName, tuple[DocumentLookupField, ...]
] = {
    PERIODIC_JOB_HEARTBEATS: (integer_field("due_by"),),
}
