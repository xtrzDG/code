from collections.abc import Callable, Sequence

from typed_time_provider import Microseconds

from app.contracts.document_store import DocumentCollectionAdapterContract
from app.contracts.jobs import (
    PeriodicJobRunRepoContract,
    PeriodicJobRunStoreAdapterContract,
    PeriodicRunDecision,
    QueuedJobClaimAdapterContract,
    QueuedJobRepoContract,
)
from app.schemas.constants.jobs import QueuedJobStatus
from app.schemas.domain.jobs import PeriodicJobRunDocument, QueuedJobDocument
from app.schemas.dto.job_queue import (
    ExpiredLeaseRelease,
    JobClaimRequest,
    JobLeaseExtension,
    PeriodicRunLease,
    QueuedJobPageQuery,
)
from app.schemas.exceptions.application_errors import NotFoundError
from app.schemas.typings.platform.constrained_integers import ProcessedItemCount
from app.schemas.typings.platform.constrained_strings import (
    JobLeaseToken,
    JobName,
    JobPeriodKey,
)
from app.schemas.typings.platform.prefixed_id import QueuedJobId
from app.schemas.typings.platform.strings import JobPayloadJson


class QueuedJobRepository(QueuedJobRepoContract):
    """
    The job queue: single jobs through the document collection, leased
    claims and other operations on many jobs through the claim adapter
    (Postgres or its in-memory twin, over the same table or collection).
    """

    def __init__(
        self,
        collection: DocumentCollectionAdapterContract[QueuedJobDocument],
        claims: QueuedJobClaimAdapterContract,
    ) -> None:
        self._collection: DocumentCollectionAdapterContract[QueuedJobDocument] = (
            collection
        )
        self._claims: QueuedJobClaimAdapterContract = claims

    def save(self, job: QueuedJobDocument) -> None:
        self._collection.upsert(str(job.id), job)

    def get(self, job_id: QueuedJobId) -> QueuedJobDocument | None:
        return self._collection.get(str(job_id))

    def claim_due(self, claim: JobClaimRequest) -> list[QueuedJobDocument]:
        return self._claims.claim_due(claim)

    def list_active_payloads(
        self,
        job_name: JobName,
        payloads: Sequence[JobPayloadJson],
    ) -> set[JobPayloadJson]:
        if not payloads:
            return set()

        return self._claims.list_active_payloads(job_name, payloads)

    def extend_leases(self, extension: JobLeaseExtension) -> list[QueuedJobId]:
        return self._claims.extend_leases(extension)

    def settle(self, job: QueuedJobDocument, lease_token: JobLeaseToken) -> bool:
        return self._collection.replace_if(
            str(job.id),
            job,
            lambda stored: (
                stored.status is QueuedJobStatus.RUNNING
                and stored.lease_token == lease_token
            ),
        )

    def release_expired_leases(
        self,
        release: ExpiredLeaseRelease,
    ) -> list[QueuedJobDocument]:
        return self._claims.release_expired_leases(release)

    def update(
        self,
        job_id: QueuedJobId,
        apply: Callable[[QueuedJobDocument], None],
    ) -> QueuedJobDocument:
        def change(stored: QueuedJobDocument) -> QueuedJobDocument:
            apply(stored)
            return stored

        updated: QueuedJobDocument | None = self._collection.modify(str(job_id), change)
        if updated is None:
            raise NotFoundError(f"Job {job_id} was not found.")

        return updated

    def list_page(self, query: QueuedJobPageQuery) -> list[QueuedJobDocument]:
        return self._claims.list_page(query)

    def purge_finished(self, finished_before: Microseconds) -> ProcessedItemCount:
        return self._claims.purge_finished(finished_before)


class PeriodicJobRunRepository(PeriodicJobRunRepoContract):
    """The run records of periodic jobs (one per job and period)."""

    def __init__(self, store: PeriodicJobRunStoreAdapterContract) -> None:
        self._store: PeriodicJobRunStoreAdapterContract = store

    def claim(
        self,
        job_name: JobName,
        period_key: JobPeriodKey,
        decide: PeriodicRunDecision,
    ) -> PeriodicJobRunDocument | None:
        return self._store.claim(job_name, period_key, decide)

    def get(
        self,
        job_name: JobName,
        period_key: JobPeriodKey,
    ) -> PeriodicJobRunDocument | None:
        return self._store.get(job_name, period_key)

    def extend_lease(self, lease: PeriodicRunLease) -> bool:
        return self._store.extend_lease(lease)

    def finish(self, run: PeriodicJobRunDocument, lease_token: JobLeaseToken) -> bool:
        return self._store.finish(run, lease_token)

    def purge_started_before(self, started_before: Microseconds) -> ProcessedItemCount:
        return self._store.purge_started_before(started_before)
