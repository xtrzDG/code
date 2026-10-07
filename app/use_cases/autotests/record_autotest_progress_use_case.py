from typed_time_provider import Microseconds, WallClock

from app.contracts.live_events import EventPublisherFacilitatorContract
from app.contracts.repositories.assistant_repositories import AutotestRunRepoContract
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.constants.assistants import AutotestRunStatus
from app.schemas.constants.live_events import LiveEventKind
from app.schemas.domain.assistants import AutotestRunDocument
from app.schemas.dto.assistants.autotest_runs import AutotestRunProgress


class RecordAutotestProgressUseCase(UseCaseContract[AutotestRunProgress, None]):
    """
    Store the scenario results a running autotest run has so far, so the
    cabinet shows live progress while the worker plays it. A run that is no
    longer RUNNING (finished or given up) is left as it is; a retried run
    starts its results again from the first scenario.
    """

    def __init__(
        self,
        autotest_run_repo: AutotestRunRepoContract,
        live_events: EventPublisherFacilitatorContract,
        wall_clock: WallClock[Microseconds],
    ) -> None:
        self._autotest_run_repo: AutotestRunRepoContract = autotest_run_repo
        self._wall_clock: WallClock[Microseconds] = wall_clock
        self._live_events: EventPublisherFacilitatorContract = live_events

    def run(self, input_data: AutotestRunProgress) -> None:
        run: AutotestRunDocument | None = self._autotest_run_repo.get(
            input_data.business_id,
            input_data.run_id,
        )
        if run is None or run.status is not AutotestRunStatus.RUNNING:
            return

        run.results = list(input_data.results)
        run.updated_at = self._wall_clock.now_unix()
        self._autotest_run_repo.save(run)
        self._live_events.publish(
            run.business_id,
            LiveEventKind.AUTOTEST_PROGRESS,
            (run.id, run.assistant_version_id),
        )
