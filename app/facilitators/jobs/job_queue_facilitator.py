from typed_time_provider import Microseconds, WallClock

from app.contracts.jobs import JobQueueFacilitatorContract, QueuedJobRepoContract
from app.schemas.domain.jobs import QueuedJobDocument
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.platform.constrained_strings import JobName
from app.schemas.typings.platform.prefixed_id import QueuedJobId
from app.schemas.typings.platform.strings import JobPayloadJson


class JobQueueFacilitator(JobQueueFacilitatorContract):
    """Puts jobs into the durable queue read by the background worker."""

    def __init__(
        self,
        job_repo: QueuedJobRepoContract,
        wall_clock: WallClock[Microseconds],
    ) -> None:
        self._job_repo: QueuedJobRepoContract = job_repo
        self._wall_clock: WallClock[Microseconds] = wall_clock

    def enqueue(
        self,
        job_name: JobName,
        payload: JobPayloadJson,
        business_id: BusinessId | None,
        run_at: Microseconds | None = None,
    ) -> QueuedJobId:
        now: Microseconds = self._wall_clock.now_unix()
        job = QueuedJobDocument(
            name=job_name,
            payload=payload,
            business_id=business_id,
            run_at=now if run_at is None else run_at,
            created_at=now,
            updated_at=now,
        )
        self._job_repo.save(job)
        return job.id
