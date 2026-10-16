from app.contracts.operator_contract import OperatorContract
from app.contracts.pipeline_contract import PipelineContract


class PipelineOperator[InputData, OutputData](OperatorContract[InputData, OutputData]):
    """
    Endpoint operator that runs one pipeline synchronously.

    Endpoints with another execution strategy (background run, retries,
    idempotency) get their own operator class.
    """

    def __init__(self, pipeline: PipelineContract[InputData, OutputData]) -> None:
        self._pipeline: PipelineContract[InputData, OutputData] = pipeline

    def operate(self, input_data: InputData) -> OutputData:
        return self._pipeline.start(input_data)
