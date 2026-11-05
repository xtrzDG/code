"""A use case wired before its target exists (the testbed builds in layers)."""

from app.contracts.use_case_contract import UseCaseContract


class DeferredUseCase[InputData, OutputData](UseCaseContract[InputData, OutputData]):
    """Forwards to `target`, which a later layer of the wiring sets."""

    def __init__(self) -> None:
        self.target: UseCaseContract[InputData, OutputData] | None = None

    def run(self, input_data: InputData) -> OutputData:
        assert self.target is not None, "The deferred use case was never wired."
        return self.target.run(input_data)
