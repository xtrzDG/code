from contextlib import AbstractContextManager, nullcontext

from typed_time_provider import Microseconds, WallClock

from app.contracts.jobs import (
    JobQueueFacilitatorContract,
    JobWakeupContract,
    QueuedJobRepoContract,
)
from app.contracts.storage import StorageUnitOfWorkContract
from app.schemas.constants.jobs import JobLane
from app.schemas.domain.jobs import QueuedJobDocument
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.platform.constrained_strings import JobName, JobSerialKey
from app.schemas.typings.platform.prefixed_id import QueuedJobId
from app.schemas.typings.platform.strings import JobPayloadJson
from app.utilities.observability.log_context import current_log_context
from app.utilities.observability.tracing.trace_context import current_trace_parent

MICROSECONDS_PER_SECOND: int = 1_000_000
# A job due within this many seconds wakes its lane exactly when it is due
# (a customer's grouped messages, a short retry); one due later is found by
# the lane's polls, at most one poll interval late, which is small next to
# its wait.
EXACT_WAKEUP_HORIZON_SECONDS: int = 600


class JobQueueFacilitator(JobQueueFacilitatorContract):
    """
    Puts jobs into the durable queue read by the background workers and
    wakes the idle threads of the job's lane: in this process, and on
    Postgres in every worker process (NOTIFY). The job row and its wake-up
    are one storage transaction (`unit_of_work`), so the signal leaves only
    once the job is committed and a woken worker always finds it. A job
    queued for later (up to EXACT_WAKEUP_HORIZON_SECONDS ahead) announces
    its due time instead, and the listening workers wake its lane then;
    the polls find any job whose wake-up was lost. A job carries
    the request id and the trace of the code that queued it, so its log
    lines and spans join that request's.
    """

    def __init__(
        self,
        job_repo: QueuedJobRepoContract,
        wall_clock: WallClock[Microseconds],
        job_wakeup: JobWakeupContract,
        unit_of_work: StorageUnitOfWorkContract | None = None,
    ) -> None:
        self._job_repo: QueuedJobRepoContract = job_repo
        self._wall_clock: WallClock[Microseconds] = wall_clock
        self._job_wakeup: JobWakeupContract = job_wakeup
        self._unit_of_work: StorageUnitOfWorkContract | None = unit_of_work

    def enqueue(
        self,
        job_name: JobName,
        payload: JobPayloadJson,
        business_id: BusinessId | None,
        run_at: Microseconds | None = None,
        lane: JobLane = JobLane.DEFAULT,
        serial_key: JobSerialKey | None = None,
    ) -> QueuedJobId:
        now: Microseconds = self._wall_clock.now_unix()
        job = QueuedJobDocument(
            name=job_name,
            payload=payload,
            business_id=business_id,
            lane=lane,
            serial_key=serial_key,
            run_at=now if run_at is None else run_at,
            request_id=current_log_context().request_id,
            trace_parent=current_trace_parent(),
            created_at=now,
            updated_at=now,
        )
        with self._transaction():
            self._job_repo.save(job)
            if job.run_at <= now:
                self._job_wakeup.notify(lane)
            elif is_within_exact_wakeup(job.run_at, now):
                self._job_wakeup.notify_at(lane, job.run_at)

        return job.id

    def _transaction(self) -> AbstractContextManager[None]:
        if self._unit_of_work is None:
            return nullcontext()

        return self._unit_of_work.unit_of_work()


def is_within_exact_wakeup(run_at: Microseconds, now: Microseconds) -> bool:
    return (
        int(run_at) - int(now) <= EXACT_WAKEUP_HORIZON_SECONDS * MICROSECONDS_PER_SECOND
    )
