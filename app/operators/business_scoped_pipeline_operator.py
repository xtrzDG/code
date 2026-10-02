from app.contracts.operator_contract import OperatorContract
from app.contracts.pipeline_contract import PipelineContract
from app.contracts.storage import StorageScopeContract
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.utilities.observability.log_context import bound_log_context
from app.utilities.storage.storage_scoping import find_operation_business_id


class BusinessScopedPipelineOperator[InputData, OutputData](
    OperatorContract[InputData, OutputData]
):
    """
    Endpoint operator that runs one pipeline synchronously inside the
    storage scope of the business its input names (concept sections 1, 2
    and 10: row-level security as the second line of defence). A request
    for business A then cannot read or write business B's tenant rows on
    Postgres even if a repository forgot its business filter. Inputs
    without a business (sign-in, webhooks, admin lists) run platform-wide;
    code that must look across businesses escalates explicitly with
    `StorageScopeContract.platform_wide()`. The business is also bound to
    the log context, so log lines and error reports of the operation name it.
    """

    def __init__(
        self,
        pipeline: PipelineContract[InputData, OutputData],
        storage_scope: StorageScopeContract,
    ) -> None:
        self._pipeline: PipelineContract[InputData, OutputData] = pipeline
        self._storage_scope: StorageScopeContract = storage_scope

    def operate(self, input_data: InputData) -> OutputData:
        business_id: BusinessId | None = find_operation_business_id(input_data)
        if business_id is None:
            return self._pipeline.start(input_data)

        with (
            bound_log_context(business_id=business_id),
            self._storage_scope.scoped_to_business(business_id),
        ):
            return self._pipeline.start(input_data)
