from app.contracts.orchestrator_contract import OrchestratorContract
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.domain.assistants import AutotestScenarioResult
from app.schemas.dto.assistants import (
    AutotestJobPayload,
    AutotestRunCompletion,
    AutotestRunFailure,
    AutotestRunPlan,
    AutotestRunView,
    AutotestScenarioRun,
)
from app.schemas.dto.jobs import JobReport, QueuedJobInput
from app.schemas.typings.platform.constrained_integers import ProcessedItemCount


class RunQueuedAutotestsOrchestrator(OrchestratorContract[QueuedJobInput, JobReport]):
    """
    Queued job "run_autotests": play every scenario of a started run, then
    store the results and set the version's status. A failure is retried
    by the worker; when the last attempt fails too, the run is given up so
    the version does not stay TESTING.
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

            raise

    def _play(self, input_data: QueuedJobInput) -> JobReport:
        plan: AutotestRunPlan = self._resume_autotest_run.run(input_data)
        if not plan.scenarios:
            return JobReport(processed_count=ProcessedItemCount(0))

        results: list[AutotestScenarioResult] = [
            self._run_autotest_scenario.run(
                AutotestScenarioRun(
                    run_id=plan.run_id,
                    business=plan.business,
                    version=plan.version,
                    scenario=scenario,
                    customer_phone_number=plan.customer_phone_number,
                )
            )
            for scenario in plan.scenarios
        ]
        self._finish_autotest_run.run(AutotestRunCompletion(plan=plan, results=results))
        return JobReport(processed_count=ProcessedItemCount(len(results)))
