from app.contracts.operator_contract import OperatorContract
from app.contracts.pipeline_contract import PipelineContract
from app.contracts.storage import StorageScopeContract


class PlatformWidePipelineOperator[InputData, OutputData](
    OperatorContract[InputData, OutputData]
):
    """
    Operator of platform-level work that must see every business's tenant
    rows: a webhook before its business is known (Telegram, Meta, payments,
    the voice platform, Google's consent), the platform admin's views, the
    demo seeding and the periodic jobs that walk all businesses. It runs
    its pipeline inside `StorageScopeContract.platform_wide()`, the explicit
    escalation of the fail-closed storage scope; code inside may narrow it
    again with `scoped_to_business(...)` once it knows the business.

    Cabinet routes of one business never use it: they run in the business's
    scope (`BusinessScopedPipelineOperator`), which
    tests/architecture_policy/test_business_routes_are_scoped.py enforces.
    """

    def __init__(
        self,
        pipeline: PipelineContract[InputData, OutputData],
        storage_scope: StorageScopeContract,
    ) -> None:
        self._pipeline: PipelineContract[InputData, OutputData] = pipeline
        self._storage_scope: StorageScopeContract = storage_scope

    def operate(self, input_data: InputData) -> OutputData:
        with self._storage_scope.platform_wide():
            return self._pipeline.start(input_data)
