from app.contracts.orchestrator_contract import OrchestratorContract
from app.contracts.use_case_contract import UseCaseContract


class UseCaseOrchestrator[InputData, OutputData](
    OrchestratorContract[InputData, OutputData]
):
    """
    Orchestrator for an endpoint that needs exactly one use case.

    Keeps the operator -> pipeline -> orchestrator -> use case chain intact
    without a hand-written pass-through class per endpoint. Flows that
    coordinate several use cases get their own orchestrator.
    """

    def __init__(self, use_case: UseCaseContract[InputData, OutputData]) -> None:
        self._use_case: UseCaseContract[InputData, OutputData] = use_case

    def execute(self, input_data: InputData) -> OutputData:
        return self._use_case.run(input_data)
