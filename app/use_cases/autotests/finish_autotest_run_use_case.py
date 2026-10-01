from typed_time_provider import Microseconds, WallClock

from app.contracts.repositories import (
    AssistantVersionRepoContract,
    AutotestRunRepoContract,
)
from app.contracts.transformer_contract import TransformerContract
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.constants.assistants import AssistantVersionStatus
from app.schemas.domain.assistants import (
    AssistantVersionDocument,
    AutotestRunDocument,
)
from app.schemas.dto.assistants import (
    AutotestRunCompletion,
    AutotestRunPlan,
    AutotestRunSummary,
    AutotestRunView,
    AutotestRunViewSource,
)
from app.schemas.exceptions.application_errors import NotFoundError
from app.utilities.assembly.autotest_evaluation import summarize_run


class FinishAutotestRunUseCase(UseCaseContract[AutotestRunCompletion, AutotestRunView]):
    """
    Store the results of a run and decide the version's fate (concept
    section 4): READY when every price and booking scenario passed and the
    average judge score is at least 4, otherwise TESTS_FAILED. The version
    keeps the average as its test score and points to the run.
    """

    def __init__(
        self,
        assistant_version_repo: AssistantVersionRepoContract,
        autotest_run_repo: AutotestRunRepoContract,
        autotest_run_view_transformer: TransformerContract[
            AutotestRunViewSource,
            AutotestRunView,
        ],
        wall_clock: WallClock[Microseconds],
    ) -> None:
        self._assistant_version_repo: AssistantVersionRepoContract = (
            assistant_version_repo
        )
        self._autotest_run_repo: AutotestRunRepoContract = autotest_run_repo
        self._autotest_run_view_transformer: TransformerContract[
            AutotestRunViewSource,
            AutotestRunView,
        ] = autotest_run_view_transformer
        self._wall_clock: WallClock[Microseconds] = wall_clock

    def run(self, input_data: AutotestRunCompletion) -> AutotestRunView:
        plan: AutotestRunPlan = input_data.plan
        version: AssistantVersionDocument | None = self._assistant_version_repo.get(
            plan.business.id,
            plan.version.id,
        )
        if version is None:
            raise NotFoundError(f"Assistant version {plan.version.id} was not found.")

        summary: AutotestRunSummary = summarize_run(input_data.results)
        now: Microseconds = self._wall_clock.now_unix()
        run = AutotestRunDocument(
            id=plan.run_id,
            business_id=plan.business.id,
            assistant_version_id=version.id,
            results=list(input_data.results),
            pass_rate=summary.pass_rate,
            average_score=summary.average_score,
            is_passed=summary.is_passed,
            created_at=plan.started_at,
            updated_at=now,
        )
        self._autotest_run_repo.save(run)

        version.status = (
            AssistantVersionStatus.READY
            if summary.is_passed
            else AssistantVersionStatus.TESTS_FAILED
        )
        version.test_score = summary.average_score
        version.autotest_run_id = run.id
        version.updated_at = now
        self._assistant_version_repo.save(version)
        return self._autotest_run_view_transformer.transform(
            AutotestRunViewSource(run=run, version=version)
        )
