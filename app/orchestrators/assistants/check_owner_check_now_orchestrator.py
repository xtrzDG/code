from app.contracts.orchestrator_contract import OrchestratorContract
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.domain.assistants import AutotestScenarioResult
from app.schemas.dto.assistants.autotest_cases import (
    OwnerCheckOutcomeView,
    OwnerCheckProbeCommand,
    OwnerCheckProbeOutcome,
    OwnerCheckProbeStart,
)
from app.schemas.dto.assistants.autotest_runs import AutotestScenarioRun


class CheckOwnerCheckNowOrchestrator(
    OrchestratorContract[OwnerCheckProbeCommand, OwnerCheckOutcomeView]
):
    """
    "Check now": one test conversation of the check against the version
    customers talk to, through the scenario runner of the autotests (the
    question word for word, its expectation, the semantic judge for words),
    then how it went, kept on the check and said in the owner's words.
    """

    def __init__(
        self,
        prepare_owner_check_probe: UseCaseContract[
            OwnerCheckProbeCommand, OwnerCheckProbeStart
        ],
        run_autotest_scenario: UseCaseContract[
            AutotestScenarioRun, AutotestScenarioResult
        ],
        record_owner_check_probe: UseCaseContract[
            OwnerCheckProbeOutcome, OwnerCheckOutcomeView
        ],
    ) -> None:
        self._prepare_owner_check_probe: UseCaseContract[
            OwnerCheckProbeCommand, OwnerCheckProbeStart
        ] = prepare_owner_check_probe
        self._run_autotest_scenario: UseCaseContract[
            AutotestScenarioRun, AutotestScenarioResult
        ] = run_autotest_scenario
        self._record_owner_check_probe: UseCaseContract[
            OwnerCheckProbeOutcome, OwnerCheckOutcomeView
        ] = record_owner_check_probe

    def execute(self, input_data: OwnerCheckProbeCommand) -> OwnerCheckOutcomeView:
        start: OwnerCheckProbeStart = self._prepare_owner_check_probe.run(input_data)
        result: AutotestScenarioResult = self._run_autotest_scenario.run(
            start.scenario_run
        )
        return self._record_owner_check_probe.run(
            OwnerCheckProbeOutcome(start=start, result=result)
        )
