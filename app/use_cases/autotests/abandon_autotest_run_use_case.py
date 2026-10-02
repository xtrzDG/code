from typed_time_provider import Microseconds, WallClock

from app.contracts.repositories.assistant_repositories import (
    AssistantVersionRepoContract,
    AutotestRunRepoContract,
)
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.constants.assistants import AssistantVersionStatus, AutotestRunStatus
from app.schemas.domain.assistants import AssistantVersionDocument, AutotestRunDocument
from app.schemas.dto.assistants import AutotestRunFailure


class AbandonAutotestRunUseCase(UseCaseContract[AutotestRunFailure, None]):
    """
    The worker gave up on an autotest run: the run is marked ERRORED and a
    version still TESTING because of it gets back the status it had before,
    so the owner can run the autotests again instead of waiting forever.
    """

    def __init__(
        self,
        assistant_version_repo: AssistantVersionRepoContract,
        autotest_run_repo: AutotestRunRepoContract,
        wall_clock: WallClock[Microseconds],
    ) -> None:
        self._assistant_version_repo: AssistantVersionRepoContract = (
            assistant_version_repo
        )
        self._autotest_run_repo: AutotestRunRepoContract = autotest_run_repo
        self._wall_clock: WallClock[Microseconds] = wall_clock

    def run(self, input_data: AutotestRunFailure) -> None:
        run: AutotestRunDocument | None = self._autotest_run_repo.get(
            input_data.business_id,
            input_data.run_id,
        )
        if run is None or run.status is not AutotestRunStatus.RUNNING:
            return

        now: Microseconds = self._wall_clock.now_unix()
        run.status = AutotestRunStatus.ERRORED
        run.updated_at = now
        self._autotest_run_repo.save(run)
        version: AssistantVersionDocument | None = self._assistant_version_repo.get(
            input_data.business_id,
            run.assistant_version_id,
        )
        if (
            version is None
            or version.status is not AssistantVersionStatus.TESTING
            or version.autotest_run_id != run.id
        ):
            return

        version.status = run.previous_version_status or AssistantVersionStatus.DRAFT
        version.updated_at = now
        self._assistant_version_repo.save(version)
