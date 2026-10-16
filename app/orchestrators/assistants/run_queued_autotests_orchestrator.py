from contextlib import suppress

from app.contracts.orchestrator_contract import OrchestratorContract
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.domain.assistants import AutotestScenarioResult
from app.schemas.dto.assistants.assistant_views import AutotestRunView
from app.schemas.dto.assistants.autotest_runs import (
    AutotestJobPayload,
    AutotestRunCompletion,
    AutotestRunFailure,
    AutotestRunPlan,
    AutotestRunProgress,
    AutotestScenarioRun,
)
from app.schemas.dto.jobs import JobReport, QueuedJobInput
from app.schemas.dto.setup.apply_changes import AppliedVersion
from app.schemas.exceptions.base_exception import ApplicationError
from app.schemas.typings.platform.constrained_integers import ProcessedItemCount


class RunQueuedAutotestsOrchestrator(OrchestratorContract[QueuedJobInput, JobReport]):
    """
    Queued job "run_autotests": play every scenario of a started run (its
    results so far are stored after each one, for live progress), then
    store the results and set the version's status. A failure is retried
    by the worker; when the last attempt fails too, the run is given up so
    the version does not stay TESTING. When the version belongs to the
    owner's "Apply changes", that apply then goes on: published when the
    checks passed, otherwise waiting for the owner with the reasons.
    """

    def __init__(
        self,
        resume_autotest_run: UseCaseContract[QueuedJobInput, AutotestRunPlan],
        run_autotest_scenario: UseCaseContract[
            AutotestScenarioRun,
            AutotestScenarioResult,
        ],
        finish_autotest_run: UseCaseContract[AutotestRunCompletion, AutotestRunView],
        abandon_autotest_run: UseCaseContract[AutotestRunFailure, None],
        record_autotest_progress: UseCaseContract[AutotestRunProgress, None],
        publish_applied_version: UseCaseContract[AppliedVersion, None],
    ) -> None:
        self._resume_autotest_run: UseCaseContract[QueuedJobInput, AutotestRunPlan] = (
            resume_autotest_run
        )
        self._run_autotest_scenario: UseCaseContract[
            AutotestScenarioRun,
            AutotestScenarioResult,
        ] = run_autotest_scenario
        self._finish_autotest_run: UseCaseContract[
            AutotestRunCompletion,
            AutotestRunView,
        ] = finish_autotest_run
        self._abandon_autotest_run: UseCaseContract[AutotestRunFailure, None] = (
            abandon_autotest_run
        )
        self._record_autotest_progress: UseCaseContract[AutotestRunProgress, None] = (
            record_autotest_progress
        )
        self._publish_applied_version: UseCaseContract[AppliedVersion, None] = (
            publish_applied_version
        )

    def execute(self, input_data: QueuedJobInput) -> JobReport:
        try:
            return self._play(input_data)
        except Exception:
            if input_data.is_final_attempt and input_data.business_id is not None:
                self._abandon_autotest_run.run(
                    AutotestRunFailure(
                        business_id=input_data.business_id,
                        run_id=AutotestJobPayload.model_validate_json(
                            str(input_data.payload)
                        ).run_id,
                    )
                )
                # The apply of the version learns that its checks stopped;
                # the job's own failure is what gets reported.
                with suppress(ApplicationError):
                    self._continue_apply(input_data)

            raise

    def _play(self, input_data: QueuedJobInput) -> JobReport:
        plan: AutotestRunPlan = self._resume_autotest_run.run(input_data)
        if not plan.scenarios:
            return JobReport(processed_count=ProcessedItemCount(0))

        results: list[AutotestScenarioResult] = []
        for scenario in plan.scenarios:
            results.append(
                self._run_autotest_scenario.run(
                    AutotestScenarioRun(
                        run_id=plan.run_id,
                        business=plan.business,
                        version=plan.version,
                        scenario=scenario,
                        customer_phone_number=plan.customer_phone_number,
                    )
                )
            )
            if len(results) < len(plan.scenarios):
                self._record_autotest_progress.run(
                    AutotestRunProgress(
                        business_id=plan.business.id,
                        run_id=plan.run_id,
                        results=list(results),
                    )
                )

        self._finish_autotest_run.run(AutotestRunCompletion(plan=plan, results=results))
        self._publish_applied_version.run(
            AppliedVersion(
                business_id=plan.business.id,
                assistant_version_id=plan.version.id,
            )
        )
        return JobReport(processed_count=ProcessedItemCount(len(results)))

    def _continue_apply(self, input_data: QueuedJobInput) -> None:
        """The checks of an apply were given up: the apply needs attention."""

        plan: AutotestRunPlan = self._resume_autotest_run.run(input_data)
        self._publish_applied_version.run(
            AppliedVersion(
                business_id=plan.business.id,
                assistant_version_id=plan.version.id,
            )
        )
