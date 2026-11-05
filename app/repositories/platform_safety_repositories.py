"""
The repositories of the platform's safety switches and watchers: the
global pause (one row), the periodic jobs' heartbeats (one row per job,
the overdue ones found by their indexed `due_by`) and the daily payment
reconciliations (one row per UTC day). Every read is keyed or indexed.
"""

from collections.abc import Sequence

from typed_time_provider import Microseconds

from app.contracts.document_store import DocumentCollectionAdapterContract
from app.contracts.platform_safety import (
    PaymentReconciliationRepoContract,
    PeriodicJobHeartbeatRepoContract,
    PlatformPauseRepoContract,
)
from app.repositories.document_queries import time_range
from app.schemas.domain.payment_reconciliations import PaymentReconciliationDocument
from app.schemas.domain.periodic_job_heartbeats import PeriodicJobHeartbeatDocument
from app.schemas.domain.platform_pauses import PlatformPauseDocument
from app.schemas.typings.billing.constrained_strings import ReconciliationDay
from app.schemas.typings.platform.constrained_strings import JobName
from app.schemas.typings.storage.constrained_integers import DocumentQueryLimit
from app.schemas.typings.storage.constrained_strings import DocumentFieldPath

PLATFORM_PAUSE_KEY: str = "platform"
DUE_BY_FIELD: DocumentFieldPath = DocumentFieldPath("due_by")


class PlatformPauseRepository(PlatformPauseRepoContract):
    """The one row of the global pause, stored under `platform`."""

    def __init__(
        self, collection: DocumentCollectionAdapterContract[PlatformPauseDocument]
    ) -> None:
        self._collection: DocumentCollectionAdapterContract[PlatformPauseDocument] = (
            collection
        )

    def get(self) -> PlatformPauseDocument | None:
        return self._collection.get(PLATFORM_PAUSE_KEY)

    def save(self, pause: PlatformPauseDocument) -> None:
        self._collection.upsert(PLATFORM_PAUSE_KEY, pause)


class PeriodicJobHeartbeatRepository(PeriodicJobHeartbeatRepoContract):
    """One row per periodic job, stored under its name."""

    def __init__(
        self,
        collection: DocumentCollectionAdapterContract[PeriodicJobHeartbeatDocument],
    ) -> None:
        self._collection: DocumentCollectionAdapterContract[
            PeriodicJobHeartbeatDocument
        ] = collection

    def get_many(
        self, job_names: Sequence[JobName]
    ) -> list[PeriodicJobHeartbeatDocument]:
        return self._collection.get_many([str(name) for name in job_names])

    def save(self, heartbeat: PeriodicJobHeartbeatDocument) -> None:
        self._collection.upsert(str(heartbeat.job_name), heartbeat)

    def list_overdue(
        self, now: Microseconds, limit: DocumentQueryLimit
    ) -> list[PeriodicJobHeartbeatDocument]:
        return self._collection.list_by_range(
            time_range(DUE_BY_FIELD, ending_before=now), limit=limit
        )

    def delete(self, job_name: JobName) -> None:
        self._collection.delete(str(job_name))


class PaymentReconciliationRepository(PaymentReconciliationRepoContract):
    """One row per UTC day, stored under the day."""

    def __init__(
        self,
        collection: DocumentCollectionAdapterContract[PaymentReconciliationDocument],
    ) -> None:
        self._collection: DocumentCollectionAdapterContract[
            PaymentReconciliationDocument
        ] = collection

    def get(self, day: ReconciliationDay) -> PaymentReconciliationDocument | None:
        return self._collection.get(str(day))

    def save(self, reconciliation: PaymentReconciliationDocument) -> None:
        self._collection.upsert(str(reconciliation.day), reconciliation)
