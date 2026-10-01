from app.contracts.orchestrator_contract import OrchestratorContract
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.domain.assistants import AutotestScenarioResult
from app.schemas.dto.assistants import (
    AutotestRunCompletion,
    AutotestRunPlan,
    AutotestRunView,
    AutotestScenarioRun,
    RunAutotestsCommand,
)


class RunAutotestsOrchestrator(
    OrchestratorContract[RunAutotestsCommand, AutotestRunView]
):
    """
    One autotest run: start it (authorize, plan scenarios, version TESTING),
    play every scenario in order, then store the results and set the
    version READY or TESTS_FAILED.
    """

    def __init__(
        self,
        start_autotest_run: UseCaseContract[RunAutotestsCommand, AutotestRunPlan],
        run_autotest_scenario: UseCaseContract[
            AutotestScenarioRun,
            AutotestScenarioResult,
        ],
        finish_autotest_run: UseCaseContract[AutotestRunCompletion, AutotestRunView],
    ) -> None:
        self._start_autotest_run: UseCaseContract[
            RunAutotestsCommand,
            AutotestRunPlan,
        ] = start_autotest_run
        self._run_autotest_scenario: UseCaseContract[
            AutotestScenarioRun,
            AutotestScenarioResult,
        ] = run_autotest_scenario
        self._finish_autotest_run: UseCaseContract[
            AutotestRunCompletion,
            AutotestRunView,
        ] = finish_autotest_run

    def execute(self, input_data: RunAutotestsCommand) -> AutotestRunView:
        plan: AutotestRunPlan = self._start_autotest_run.run(input_data)
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
        return self._finish_autotest_run.run(
            AutotestRunCompletion(plan=plan, results=results)
        )
