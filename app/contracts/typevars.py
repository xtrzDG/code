from typing import TypeVar

InputData = TypeVar("InputData", contravariant=True)
OutputData = TypeVar("OutputData", covariant=True)
