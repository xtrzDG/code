from app.contracts.orchestrator_contract import OrchestratorContract
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.domain.assistants import AutotestScenarioResult
from app.schemas.dto.assistants.assistant_commands import RunAutotestsCommand
from app.schemas.dto.assistants.assistant_views import AutotestRunView
from app.schemas.dto.assistants.autotest_runs import (
    AutotestRunCompletion,
    AutotestRunPlan,
    AutotestScenarioRun,
)
from app.schemas.dto.voice_checks import VoiceCheckRun
from app.utilities.assembly.voice_check_runs import split_voice_checks, voice_check_run


class RunAutotestsOrchestrator(
    OrchestratorContract[RunAutotestsCommand, AutotestRunView]
):
    """
    One autotest run: start it (authorize, plan scenarios, version TESTING),
    play every chat scenario in order and the voice checks together, then
    store the results and set the version READY or TESTS_FAILED.
    """

    def __init__(
        self,
        start_autotest_run: UseCaseContract[RunAutotestsCommand, AutotestRunPlan],
        run_autotest_scenario: UseCaseContract[
            AutotestScenarioRun,
            AutotestScenarioResult,
        ],
        finish_autotest_run: UseCaseContract[AutotestRunCompletion, AutotestRunView],
        run_voice_checks: UseCaseContract[VoiceCheckRun, list[AutotestScenarioResult]],
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
        self._run_voice_checks: UseCaseContract[
            VoiceCheckRun, list[AutotestScenarioResult]
        ] = run_voice_checks

    def execute(self, input_data: RunAutotestsCommand) -> AutotestRunView:
        plan: AutotestRunPlan = self._start_autotest_run.run(input_data)
        chats, calls = split_voice_checks(plan.scenarios)
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
            for scenario in chats
        ] + self._run_voice_checks.run(voice_check_run(plan, calls))
        return self._finish_autotest_run.run(
            AutotestRunCompletion(plan=plan, results=results)
        )
