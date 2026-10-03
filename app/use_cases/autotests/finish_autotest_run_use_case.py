from typed_time_provider import Microseconds, WallClock

from app.contracts.live_events import EventPublisherFacilitatorContract
from app.contracts.repositories.assistant_repositories import (
    AssistantVersionRepoContract,
    AutotestRunRepoContract,
)
from app.contracts.transformer_contract import TransformerContract
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.constants.assistants import AutotestRunStatus
from app.schemas.constants.live_events import LiveEventKind
from app.schemas.domain.assistants import (
    AssistantVersionDocument,
    AutotestRunDocument,
)
from app.schemas.dto.assistants.assistant_views import AutotestRunView
from app.schemas.dto.assistants.autotest_runs import (
    AutotestRunCompletion,
    AutotestRunPlan,
    AutotestRunSummary,
    AutotestRunViewSource,
)
from app.schemas.exceptions.application_errors import NotFoundError
from app.utilities.assembly.autotest_evaluation import (
    decide_version_status,
    summarize_run,
)


class FinishAutotestRunUseCase(UseCaseContract[AutotestRunCompletion, AutotestRunView]):
    """
    Store the results of a run and decide the version's fate (concept
    section 4): READY when every price and booking scenario passed and the
    average judge score is at least 4, otherwise TESTS_FAILED.

    Only a run that covered every version language and every applicable
    scenario kind, or the quick check "Apply changes" chose for the changes
    it carries, can make a version READY; a narrowed run that passes
    proves nothing new and leaves the version as it was before the run (a
    failed version stays failed), while a narrowed run that fails still
    fails the version. The average of a full run or of the quick check
    becomes the version's test score. The version points to the run.
    """

    def __init__(
        self,
        assistant_version_repo: AssistantVersionRepoContract,
        autotest_run_repo: AutotestRunRepoContract,
        autotest_run_view_transformer: TransformerContract[
            AutotestRunViewSource,
            AutotestRunView,
        ],
        live_events: EventPublisherFacilitatorContract,
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
        self._live_events: EventPublisherFacilitatorContract = live_events

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
        run: AutotestRunDocument = self._autotest_run_repo.get(
            plan.business.id,
            plan.run_id,
        ) or AutotestRunDocument(
            id=plan.run_id,
            business_id=plan.business.id,
            assistant_version_id=version.id,
            is_full_coverage=plan.is_full_coverage,
            previous_version_status=plan.previous_version_status,
            created_at=plan.started_at,
            updated_at=now,
        )
        run.status = AutotestRunStatus.FINISHED
        run.results = list(input_data.results)
        run.pass_rate = summary.pass_rate
        run.average_score = summary.average_score
        run.is_passed = summary.is_passed
        run.updated_at = now

        version.status = decide_version_status(
            is_passed=summary.is_passed,
            is_full_coverage=plan.is_full_coverage,
            previous_status=plan.previous_version_status,
            is_smoke_check=plan.smoke_check is not None,
        )
        if plan.is_full_coverage or plan.smoke_check is not None:
            version.test_score = summary.average_score

        version.autotest_run_id = run.id
        version.updated_at = now
        # The version first: whoever sees the run finished (the cabinet
        # polls it) also sees the version's final status. A crash between
        # the two writes leaves the run RUNNING, so the job's retry plays
        # it again and lands on the same status.
        self._assistant_version_repo.save(version)
        self._autotest_run_repo.save(run)
        self._live_events.publish(
            run.business_id,
            LiveEventKind.AUTOTEST_PROGRESS,
            (run.id, run.assistant_version_id),
        )
        return self._autotest_run_view_transformer.transform(
            AutotestRunViewSource(run=run, version=version)
        )
