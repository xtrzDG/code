from app.contracts.orchestrator_contract import OrchestratorContract
from app.contracts.pipeline_contract import PipelineContract


class OrchestratorPipeline[InputData, OutputData](
    PipelineContract[InputData, OutputData]
):
    """
    Pipeline whose execution phase has a single orchestrator.

    Multi-orchestrator phases (assembly followed by autotests, customer message
    handling) get their own pipeline class.
    """

    def __init__(
        self,
        orchestrator: OrchestratorContract[InputData, OutputData],
    ) -> None:
        self._orchestrator: OrchestratorContract[InputData, OutputData] = orchestrator

    def start(self, input_data: InputData) -> OutputData:
        return self._orchestrator.execute(input_data)
