from typed_time_provider import Microseconds, WallClock

from app.contracts.monitoring import SystemHealthRepoContract
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.constants.jobs import JobLane
from app.schemas.domain.jobs import QueuedJobDocument
from app.schemas.dto.telemetry import JobQueueMeasurement, JobQueueQuery, LaneDepth
from app.schemas.typings.monitoring.constrained_integers import (
    LaneJobCount,
    WaitSeconds,
)

MICROSECONDS_PER_SECOND: int = 1_000_000


class MeasureJobQueuesUseCase(UseCaseContract[JobQueueQuery, JobQueueMeasurement]):
    """
    The job queue for a metrics scrape (platform-wide): each lane's jobs
    due now and the oldest one's wait, and the dead letters by job name.
    Each figure is an indexed count or one indexed row, so a scrape every
    15 s costs the database nothing worth noting.
    """

    def __init__(
        self,
        system_health_repo: SystemHealthRepoContract,
        wall_clock: WallClock[Microseconds],
    ) -> None:
        self._health: SystemHealthRepoContract = system_health_repo
        self._wall_clock: WallClock[Microseconds] = wall_clock

    def run(self, input_data: JobQueueQuery) -> JobQueueMeasurement:
        del input_data
        now: Microseconds = self._wall_clock.now_unix()
        return JobQueueMeasurement(
            lanes=[self._lane(lane, now) for lane in JobLane],
            dead_jobs=self._health.count_dead_jobs_by_name(),
        )

    def _lane(self, lane: JobLane, now: Microseconds) -> LaneDepth:
        due: int = int(self._health.count_due_jobs(lane, now))
        oldest: QueuedJobDocument | None = (
            self._health.find_oldest_due_job(lane, now) if due else None
        )
        return LaneDepth(
            lane=lane,
            due_jobs=LaneJobCount(due),
            oldest_wait_seconds=(
                None
                if oldest is None
                else WaitSeconds(
                    max(0, int(now) - int(oldest.run_at)) // MICROSECONDS_PER_SECOND
                )
            ),
        )
