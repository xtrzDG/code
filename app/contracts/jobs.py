"""
Background work: the leased job queue, periodic job runs and job handlers.

Several workers (processes or threads) share one queue: a job is claimed
with a lease before it runs, so no two workers run it at once, and a job
whose worker died is released when its lease ends. Periodic jobs record
their run per period, so a restart or a second worker never repeats one.
"""

from collections.abc import Callable, Sequence
from contextlib import AbstractContextManager
from typing import Protocol

from typed_time_provider import Microseconds

from app.contracts.adapter_contract import AdapterContract
from app.contracts.facilitator_contract import FacilitatorContract
from app.contracts.operator_contract import OperatorContract
from app.contracts.repo_contract import RepoContract
from app.contracts.utility_contract import UtilityContract
from app.schemas.constants.jobs import JobLane
from app.schemas.domain.jobs import PeriodicJobRunDocument, QueuedJobDocument
from app.schemas.dto.job_queue import (
    ExpiredLeaseRelease,
    HeldJobLease,
    JobClaimRequest,
    JobLeaseExtension,
    PeriodicRunLease,
    QueuedJobPageQuery,
)
from app.schemas.dto.jobs import JobReport, JobTick, QueuedJobInput
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.platform.constrained_integers import ProcessedItemCount
from app.schemas.typings.platform.constrained_strings import (
    JobLeaseToken,
    JobName,
    JobPeriodKey,
    JobSerialKey,
)
from app.schemas.typings.platform.prefixed_id import QueuedJobId
from app.schemas.typings.platform.strings import JobPayloadJson

type PeriodicJobOperator = OperatorContract[JobTick, JobReport]
type QueuedJobOperator = OperatorContract[QueuedJobInput, JobReport]
type PeriodicRunDecision = Callable[
    [PeriodicJobRunDocument | None],
    PeriodicJobRunDocument | None,
]


class QueuedJobClaimAdapterContract(AdapterContract, Protocol):
    """
    Operations on many queued jobs at once, each atomic: on Postgres one
    statement (FOR UPDATE SKIP LOCKED for claims), in memory under one lock.
    Collection-level reads and writes of single jobs go through the
    document collection.
    """

    def claim_due(self, claim: JobClaimRequest) -> list[QueuedJobDocument]:
        raise NotImplementedError

    def extend_leases(self, extension: JobLeaseExtension) -> list[QueuedJobId]:
        """The jobs whose lease was extended (the others were lost)."""
        raise NotImplementedError

    def release_expired_leases(
        self,
        release: ExpiredLeaseRelease,
    ) -> list[QueuedJobDocument]:
        """The released jobs as stored afterwards (PENDING or DEAD)."""
        raise NotImplementedError

    def list_page(self, query: QueuedJobPageQuery) -> list[QueuedJobDocument]:
        raise NotImplementedError

    def purge_finished(self, finished_before: Microseconds) -> ProcessedItemCount:
        """Delete DONE, DEAD and DISCARDED jobs last changed before then."""
        raise NotImplementedError

    def list_active_payloads(
        self,
        job_name: JobName,
        payloads: Sequence[JobPayloadJson],
    ) -> set[JobPayloadJson]:
        """The payloads among these of a PENDING or RUNNING job of the name."""
        raise NotImplementedError


class PeriodicJobRunStoreAdapterContract(AdapterContract, Protocol):
    """
    The run records of periodic jobs, one per job and period. A start is
    decided under a lock per job name (Postgres: `pg_try_advisory_xact_lock`),
    so exactly one worker may start a job in a period; a worker that cannot
    take the lock right away leaves the job to the one holding it.
    """

    def claim(
        self,
        job_name: JobName,
        period_key: JobPeriodKey,
        decide: PeriodicRunDecision,
    ) -> PeriodicJobRunDocument | None:
        """
        Under the lock of `job_name`: read the run of the period (None when
        there is none), let `decide` return the run to store, store it and
        return it. None, and nothing stored, when the lock is taken or
        `decide` returns None.
        """
        raise NotImplementedError

    def get(
        self,
        job_name: JobName,
        period_key: JobPeriodKey,
    ) -> PeriodicJobRunDocument | None:
        raise NotImplementedError

    def extend_lease(self, lease: PeriodicRunLease) -> bool:
        """Move the lease of a RUNNING run held under the lease's token."""
        raise NotImplementedError

    def finish(self, run: PeriodicJobRunDocument, lease_token: JobLeaseToken) -> bool:
        """Store the finished run only while it is RUNNING under `lease_token`."""
        raise NotImplementedError

    def purge_started_before(self, started_before: Microseconds) -> ProcessedItemCount:
        """Delete the runs of periods that first started before then."""
        raise NotImplementedError


class QueuedJobRepoContract(RepoContract, Protocol):
    def save(self, job: QueuedJobDocument) -> None:
        raise NotImplementedError

    def get(self, job_id: QueuedJobId) -> QueuedJobDocument | None:
        raise NotImplementedError

    def claim_due(self, claim: JobClaimRequest) -> list[QueuedJobDocument]:
        """Lease due jobs of one lane (see `JobClaimRequest`)."""
        raise NotImplementedError

    def extend_leases(self, extension: JobLeaseExtension) -> list[QueuedJobId]:
        raise NotImplementedError

    def settle(self, job: QueuedJobDocument, lease_token: JobLeaseToken) -> bool:
        """
        Store the outcome of a run (DONE, PENDING for a retry, DEAD) only if
        the job is still RUNNING under `lease_token`. False when the lease
        was lost: another worker owns the job now and nothing is written.
        """
        raise NotImplementedError

    def release_expired_leases(
        self,
        release: ExpiredLeaseRelease,
    ) -> list[QueuedJobDocument]:
        raise NotImplementedError

    def hand_back(self, lease: HeldJobLease, now: Microseconds) -> bool:
        """
        A stopping worker gives a job it still runs back to the queue: due
        `now`, the cut-off attempt not counted (`hand_back_job`). False when
        the job no longer runs under the lease's token.
        """
        raise NotImplementedError

    def update(
        self,
        job_id: QueuedJobId,
        apply: Callable[[QueuedJobDocument], None],
    ) -> QueuedJobDocument:
        """
        Apply a change to the job as stored now and store it in one step.
        `apply` may raise to refuse (nothing is stored). NotFoundError when
        the job does not exist.
        """
        raise NotImplementedError

    def list_page(self, query: QueuedJobPageQuery) -> list[QueuedJobDocument]:
        raise NotImplementedError

    def purge_finished(self, finished_before: Microseconds) -> ProcessedItemCount:
        raise NotImplementedError

    def list_active_payloads(
        self,
        job_name: JobName,
        payloads: Sequence[JobPayloadJson],
    ) -> set[JobPayloadJson]:
        """
        The payloads among these that a job of the name still waits or runs
        with: their work is not lost.
        """
        raise NotImplementedError


class PeriodicJobRunRepoContract(RepoContract, Protocol):
    def claim(
        self,
        job_name: JobName,
        period_key: JobPeriodKey,
        decide: PeriodicRunDecision,
    ) -> PeriodicJobRunDocument | None:
        """
        The run this worker may start now, as `decide` builds it from the
        stored run of the period (see `decide_periodic_run_start`), or None
        when `decide` refuses or another worker is deciding right now.
        """
        raise NotImplementedError

    def get(
        self,
        job_name: JobName,
        period_key: JobPeriodKey,
    ) -> PeriodicJobRunDocument | None:
        raise NotImplementedError

    def extend_lease(self, lease: PeriodicRunLease) -> bool:
        raise NotImplementedError

    def finish(self, run: PeriodicJobRunDocument, lease_token: JobLeaseToken) -> bool:
        """Store the finished run only while it is held under `lease_token`."""
        raise NotImplementedError

    def purge_started_before(self, started_before: Microseconds) -> ProcessedItemCount:
        raise NotImplementedError


class JobQueueFacilitatorContract(FacilitatorContract, Protocol):
    def enqueue(
        self,
        job_name: JobName,
        payload: JobPayloadJson,
        business_id: BusinessId | None,
        run_at: Microseconds | None = None,
        lane: JobLane = JobLane.DEFAULT,
        serial_key: JobSerialKey | None = None,
    ) -> QueuedJobId:
        """
        Queue a job to run at `run_at` (now when omitted) in `lane`. Jobs
        with the same `serial_key` run one at a time, oldest first.
        """
        raise NotImplementedError


class JobWakeupContract(UtilityContract, Protocol):
    """
    The signal "a job was queued in this lane" (or "will be due then"):
    idle lane threads start at once, or when the job is due, instead of at
    their next poll. In memory it reaches the threads of
    the same process; on Postgres (NOTIFY on `workshop_jobs`) the worker
    processes that `listen`. A lost or spurious wake-up costs only one poll
    interval or one empty claim: a woken thread claims from the queue.
    """

    def notify(self, lane: JobLane) -> None:
        """
        Signal `lane`. Called inside the enqueue's storage transaction, the
        signal leaves when the job is committed, never before.
        """
        raise NotImplementedError

    def notify_at(self, lane: JobLane, run_at: Microseconds) -> None:
        """
        Signal that a job of `lane` becomes due at `run_at`: the listening
        workers wake the lane then, instead of at its next poll. Called
        inside the enqueue's storage transaction like `notify`, so it
        leaves only once the job is committed.
        """
        raise NotImplementedError

    def wait(self, lane: JobLane, timeout_seconds: float) -> bool:
        """
        Wait until `lane` is notified or the timeout passes; True when it
        was notified. A notification that came before the wait counts.
        """
        raise NotImplementedError

    def listen(self) -> AbstractContextManager[None]:
        """
        Receive the signals of every process for the block (a worker while
        its lane threads run); outside it only this process's own count.
        """
        raise NotImplementedError
