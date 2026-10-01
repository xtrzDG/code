from typing import Protocol

from app.contracts.base_contract import BaseContract
from app.contracts.typevars import InputData, OutputData


class PipelineContract(BaseContract, Protocol[InputData, OutputData]):
    def start(self, input_data: InputData) -> OutputData:
        raise NotImplementedError
