import threading
from functools import partial

from typed_time_provider import Microseconds

from app.contracts.document_store import DocumentCollectionAdapterContract
from app.contracts.jobs import QueuedJobClaimAdapterContract
from app.schemas.constants.jobs import QueuedJobStatus
from app.schemas.domain.jobs import QueuedJobDocument
from app.schemas.dto.job_queue import (
    ExpiredLeaseRelease,
    JobClaimRequest,
    JobLeaseExtension,
    QueuedJobPageQuery,
)
from app.schemas.typings.platform.constrained_integers import (
    JobAttemptCount,
    ProcessedItemCount,
)
from app.schemas.typings.platform.constrained_strings import (
    JobLeaseToken,
    JobSerialKey,
)
from app.schemas.typings.platform.prefixed_id import QueuedJobId

STATUS_FIELD: str = "status"
FINISHED_STATUSES: frozenset[QueuedJobStatus] = frozenset(
    {QueuedJobStatus.DONE, QueuedJobStatus.DEAD, QueuedJobStatus.DISCARDED}
)


class InMemoryQueuedJobClaimAdapter(QueuedJobClaimAdapterContract):
    """
    The in-process twin of the Postgres job claims (tests, development
    without DATABASE_URL): the same rules, made atomic by one lock that every
    claim, heartbeat and release of this queue takes. Correct as long as all
    workers of the queue live in this process, which in-memory storage
    implies anyway.
    """

    def __init__(
        self,
        collection: DocumentCollectionAdapterContract[QueuedJobDocument],
    ) -> None:
        self._collection: DocumentCollectionAdapterContract[QueuedJobDocument] = (
            collection
        )
        self._lock: threading.Lock = threading.Lock()

    def claim_due(self, claim: JobClaimRequest) -> list[QueuedJobDocument]:
        with self._lock:
            busy_keys: set[JobSerialKey] = {
                job.serial_key
                for job in self._with_status(QueuedJobStatus.RUNNING)
                if job.serial_key is not None
            }
            due: list[QueuedJobDocument] = sorted(
                (
                    job
                    for job in self._with_status(QueuedJobStatus.PENDING)
                    if job.lane is claim.lane and job.run_at <= claim.now
                ),
                key=lambda job: job.run_at,
            )
            claimed: list[QueuedJobDocument] = []
            for job in due:
                if len(claimed) >= int(claim.limit):
                    break

                if job.serial_key is not None:
                    if job.serial_key in busy_keys:
                        continue

                    busy_keys.add(job.serial_key)

                stored: QueuedJobDocument | None = self._collection.modify(
                    str(job.id),
                    lambda current: lease_job(current, claim),
                )
                if stored is not None:
                    claimed.append(stored)

        return claimed

    def extend_leases(self, extension: JobLeaseExtension) -> list[QueuedJobId]:
        extended: list[QueuedJobId] = []
        with self._lock:
            for lease in extension.leases:
                stored: QueuedJobDocument | None = self._collection.modify(
                    str(lease.job_id),
                    partial(
                        extend_lease,
                        lease_token=lease.lease_token,
                        lease_until=extension.lease_until,
                    ),
                )
                if stored is not None:
                    extended.append(lease.job_id)

        return extended

    def release_expired_leases(
        self,
        release: ExpiredLeaseRelease,
    ) -> list[QueuedJobDocument]:
        released: list[QueuedJobDocument] = []
        with self._lock:
            for job in self._with_status(QueuedJobStatus.RUNNING):
                stored: QueuedJobDocument | None = self._collection.modify(
                    str(job.id),
                    lambda current: release_expired(current, release),
                )
                if stored is not None:
                    released.append(stored)

        return released

    def list_page(self, query: QueuedJobPageQuery) -> list[QueuedJobDocument]:
        jobs: list[QueuedJobDocument] = [
            job
            for job in self._collection.list_all()
            if (query.status is None or job.status is query.status)
            and (query.name is None or job.name == query.name)
        ]
        ordered: list[QueuedJobDocument] = sorted(
            jobs,
            key=lambda job: (int(job.updated_at), str(job.id)),
            reverse=True,
        )
        if query.after is not None:
            position: tuple[int, str] = (
                int(query.after.updated_at),
                str(query.after.job_id),
            )
            ordered = [
                job for job in ordered if (int(job.updated_at), str(job.id)) < position
            ]

        return ordered[: int(query.page_size) + 1]

    def purge_finished(self, finished_before: Microseconds) -> ProcessedItemCount:
        purged: int = 0
        with self._lock:
            for job in self._collection.list_all():
                if job.status in FINISHED_STATUSES and job.updated_at < finished_before:
                    self._collection.delete(str(job.id))
                    purged += 1

        return ProcessedItemCount(purged)

    def _with_status(self, status: QueuedJobStatus) -> list[QueuedJobDocument]:
        return self._collection.list_by_field(STATUS_FIELD, status.value)


def lease_job(
    current: QueuedJobDocument,
    claim: JobClaimRequest,
) -> QueuedJobDocument | None:
    """The job claimed under `claim`, or None when it is no longer pending."""

    if current.status is not QueuedJobStatus.PENDING:
        return None

    current.status = QueuedJobStatus.RUNNING
    current.attempts = JobAttemptCount(int(current.attempts) + 1)
    current.lease_until = claim.lease_until
    current.lease_token = claim.lease_token
    current.updated_at = claim.now
    return current


def extend_lease(
    current: QueuedJobDocument,
    lease_token: JobLeaseToken,
    lease_until: Microseconds,
) -> QueuedJobDocument | None:
    """The job with its lease moved, or None when the lease is not held."""

    if current.status is not QueuedJobStatus.RUNNING:
        return None

    if current.lease_token != lease_token:
        return None

    current.lease_until = lease_until
    return current


def release_expired(
    current: QueuedJobDocument,
    release: ExpiredLeaseRelease,
) -> QueuedJobDocument | None:
    """
    A running job whose lease ended, back to PENDING (due now) or DEAD after
    its last attempt; None when its lease is still alive.
    """

    if current.status is not QueuedJobStatus.RUNNING:
        return None

    if current.lease_until is not None and current.lease_until >= release.now:
        return None

    current.status = (
        QueuedJobStatus.DEAD
        if current.attempts >= release.max_attempts
        else QueuedJobStatus.PENDING
    )
    current.run_at = release.now
    current.lease_until = None
    current.lease_token = None
    current.last_error = release.error_text
    current.updated_at = release.now
    return current
