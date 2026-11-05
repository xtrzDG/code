from app.contracts.orchestrator_contract import OrchestratorContract
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.dto.assistants.assistant_commands import RunAutotestsCommand
from app.schemas.dto.assistants.assistant_views import AutotestRunView
from app.schemas.dto.assistants.autotest_runs import AutotestRunPlan


class QueueAutotestRunOrchestrator(
    OrchestratorContract[RunAutotestsCommand, AutotestRunView]
):
    """
    Start an autotest run in the request (authorize, plan, run RUNNING,
    version TESTING) and leave playing it to the background worker.
    """

    def __init__(
        self,
        start_autotest_run: UseCaseContract[RunAutotestsCommand, AutotestRunPlan],
        enqueue_autotest_run: UseCaseContract[AutotestRunPlan, AutotestRunView],
    ) -> None:
        self._start_autotest_run: UseCaseContract[
            RunAutotestsCommand,
            AutotestRunPlan,
        ] = start_autotest_run
        self._enqueue_autotest_run: UseCaseContract[
            AutotestRunPlan,
            AutotestRunView,
        ] = enqueue_autotest_run

    def execute(self, input_data: RunAutotestsCommand) -> AutotestRunView:
        plan: AutotestRunPlan = self._start_autotest_run.run(input_data)
        return self._enqueue_autotest_run.run(plan)
