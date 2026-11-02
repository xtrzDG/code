from typed_time_provider import Microseconds, WallClock

from app.contracts.live_events import EventPublisherFacilitatorContract
from app.contracts.repositories.assistant_repositories import (
    AssistantVersionRepoContract,
    AutotestRunRepoContract,
)
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.constants.assistants import AutotestRunStatus
from app.schemas.domain.assistants import AutotestRunDocument
from app.schemas.dto.assistants.autotest_runs import AutotestRunFailure
from app.use_cases.autotests.run_give_up import give_up_run


class AbandonAutotestRunUseCase(UseCaseContract[AutotestRunFailure, None]):
    """
    The worker gave up on an autotest run: the run is marked ERRORED and a
    version still TESTING because of it gets back the status it had before,
    so the owner can run the autotests again instead of waiting forever
    (run_give_up.py).
    """

    def __init__(
        self,
        assistant_version_repo: AssistantVersionRepoContract,
        autotest_run_repo: AutotestRunRepoContract,
        live_events: EventPublisherFacilitatorContract,
        wall_clock: WallClock[Microseconds],
    ) -> None:
        self._assistant_version_repo: AssistantVersionRepoContract = (
            assistant_version_repo
        )
        self._autotest_run_repo: AutotestRunRepoContract = autotest_run_repo
        self._wall_clock: WallClock[Microseconds] = wall_clock
        self._live_events: EventPublisherFacilitatorContract = live_events

    def run(self, input_data: AutotestRunFailure) -> None:
        run: AutotestRunDocument | None = self._autotest_run_repo.get(
            input_data.business_id,
            input_data.run_id,
        )
        if run is None or run.status is not AutotestRunStatus.RUNNING:
            return

        give_up_run(
            self._assistant_version_repo,
            self._autotest_run_repo,
            self._live_events,
            run,
            self._wall_clock.now_unix(),
        )
