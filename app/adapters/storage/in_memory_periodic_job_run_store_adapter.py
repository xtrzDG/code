import threading

from typed_time_provider import Microseconds

from app.adapters.storage.periodic_job_run_records import (
    PeriodicJobRunRecords,
    periodic_run_key,
)
from app.contracts.document_store import DocumentCollectionAdapterContract
from app.contracts.jobs import (
    PeriodicJobRunStoreAdapterContract,
    PeriodicRunDecision,
)
from app.schemas.domain.jobs import PeriodicJobRunDocument
from app.schemas.typings.platform.constrained_integers import ProcessedItemCount
from app.schemas.typings.platform.constrained_strings import JobName, JobPeriodKey


class InMemoryPeriodicJobRunStoreAdapter(
    PeriodicJobRunRecords,
    PeriodicJobRunStoreAdapterContract,
):
    """
    The in-process twin of the Postgres periodic run store: a try-lock per
    job name stands for `pg_try_advisory_xact_lock`, so a thread that finds
    the job being decided by another thread leaves it alone.
    """

    def __init__(
        self,
        collection: DocumentCollectionAdapterContract[PeriodicJobRunDocument],
    ) -> None:
        super().__init__(collection)
        self._locks_guard: threading.Lock = threading.Lock()
        self._locks: dict[JobName, threading.Lock] = {}

    def claim(
        self,
        job_name: JobName,
        period_key: JobPeriodKey,
        decide: PeriodicRunDecision,
    ) -> PeriodicJobRunDocument | None:
        lock: threading.Lock = self._lock_for(job_name)
        if not lock.acquire(blocking=False):
            return None

        try:
            document_key: str = periodic_run_key(job_name, period_key)
            decided: PeriodicJobRunDocument | None = decide(
                self._collection.get(document_key)
            )
            if decided is None:
                return None

            self._collection.upsert(document_key, decided)
            return self._collection.get(document_key)
        finally:
            lock.release()

    def purge_started_before(self, started_before: Microseconds) -> ProcessedItemCount:
        return ProcessedItemCount(self._delete_started_before(started_before))

    def _lock_for(self, job_name: JobName) -> threading.Lock:
        with self._locks_guard:
            lock: threading.Lock | None = self._locks.get(job_name)
            if lock is None:
                lock = threading.Lock()
                self._locks[job_name] = lock

            return lock
