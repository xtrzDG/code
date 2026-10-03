"""
Reading and settling periodic job runs over their document collection; the
start of a run (under a lock) is up to each store.
"""

from typed_time_provider import Microseconds

from app.contracts.document_store import DocumentCollectionAdapterContract
from app.schemas.constants.jobs import PeriodicJobRunStatus
from app.schemas.domain.jobs import PeriodicJobRunDocument
from app.schemas.dto.job_queue import PeriodicRunLease
from app.schemas.typings.platform.constrained_strings import (
    JobLeaseToken,
    JobName,
    JobPeriodKey,
)


def periodic_run_key(job_name: JobName, period_key: JobPeriodKey) -> str:
    """Storage key of the run of one job in one period (technical value)."""

    return f"{job_name}:{period_key}"


def is_held(stored: PeriodicJobRunDocument, lease_token: JobLeaseToken) -> bool:
    return (
        stored.status is PeriodicJobRunStatus.RUNNING
        and stored.lease_token == lease_token
    )


class PeriodicJobRunRecords:
    """Get, heartbeat and finish of periodic runs, shared by both stores."""

    def __init__(
        self,
        collection: DocumentCollectionAdapterContract[PeriodicJobRunDocument],
    ) -> None:
        self._collection: DocumentCollectionAdapterContract[PeriodicJobRunDocument] = (
            collection
        )

    def get(
        self,
        job_name: JobName,
        period_key: JobPeriodKey,
    ) -> PeriodicJobRunDocument | None:
        return self._collection.get(periodic_run_key(job_name, period_key))

    def extend_lease(self, lease: PeriodicRunLease) -> bool:
        def extend(stored: PeriodicJobRunDocument) -> PeriodicJobRunDocument | None:
            if not is_held(stored, lease.lease_token):
                return None

            stored.lease_until = lease.lease_until
            return stored

        return (
            self._collection.modify(
                periodic_run_key(lease.job_name, lease.period_key),
                extend,
            )
            is not None
        )

    def finish(self, run: PeriodicJobRunDocument, lease_token: JobLeaseToken) -> bool:
        return self._collection.replace_if(
            periodic_run_key(run.job_name, run.period_key),
            run,
            lambda stored: is_held(stored, lease_token),
        )

    def _delete_started_before(self, started_before: Microseconds) -> int:
        """Delete old runs one by one (the in-memory store's purge)."""

        purged: int = 0
        for run in self._collection.list_all():
            if run.created_at < started_before:
                self._collection.delete(periodic_run_key(run.job_name, run.period_key))
                purged += 1

        return purged
