import logging

from typed_time_provider import Microseconds, WallClock

from app.contracts.health import WorkerHeartbeatRepoContract
from app.contracts.monitoring import SystemHealthRepoContract
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.constants.jobs import JobLane
from app.schemas.dto.pipeline_health import PipelineHealthQuery, PipelineHealthReport
from app.schemas.exceptions.base_exception import ApplicationError
from app.utilities.monitoring.pipeline_health import (
    assess_pipeline,
    unreadable_pipeline,
)

LOGGER: logging.Logger = logging.getLogger(__name__)


class CheckPipelineHealthUseCase(
    UseCaseContract[PipelineHealthQuery, PipelineHealthReport]
):
    """
    GET /healthz/pipeline: whether customers' messages flow through the
    workers, read from the API's side (app/utilities/monitoring/
    pipeline_health.py): the freshest worker pulse and the oldest due
    customer message. Three indexed reads, platform-wide.

    It does not run on a worker, so the external uptime monitor sees a
    dead or stuck worker through it (docs/operations/slo.md) while
    GET /readyz stays 200 (the API itself serves). A database that cannot
    be read reports STALLED: nothing vouches for the workers. Never
    raises.
    """

    def __init__(
        self,
        worker_heartbeat_repo: WorkerHeartbeatRepoContract,
        system_health_repo: SystemHealthRepoContract,
        wall_clock: WallClock[Microseconds],
    ) -> None:
        self._worker_heartbeat_repo: WorkerHeartbeatRepoContract = worker_heartbeat_repo
        self._system_health_repo: SystemHealthRepoContract = system_health_repo
        self._wall_clock: WallClock[Microseconds] = wall_clock

    def run(self, input_data: PipelineHealthQuery) -> PipelineHealthReport:
        del input_data
        now: Microseconds = self._wall_clock.now_unix()
        try:
            return assess_pipeline(
                self._worker_heartbeat_repo.find_freshest(),
                self._system_health_repo.find_oldest_due_job(JobLane.INBOUND, now),
                int(self._system_health_repo.count_due_jobs(JobLane.INBOUND, now)),
                now,
            )
        except ApplicationError as error:
            LOGGER.warning("The pipeline's health cannot be read: %s", error)
            return unreadable_pipeline()
