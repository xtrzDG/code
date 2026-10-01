from typing import Protocol

from app.contracts.base_contract import BaseContract
from app.contracts.typevars import InputData, OutputData


class OrchestratorContract(BaseContract, Protocol[InputData, OutputData]):
    def execute(self, input_data: InputData) -> OutputData:
        raise NotImplementedError
