import json
from typing import cast

from app.contracts.operator_contract import OperatorContract
from app.contracts.pipeline_contract import PipelineContract
from app.contracts.storage import StorageScopeContract
from app.schemas.dto.jobs import QueuedJobInput
from app.schemas.exceptions.application_errors import AccessDeniedError
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.utilities.observability.log_context import bound_log_context
from app.utilities.observability.security_events import log_security_event
from app.utilities.storage.storage_scoping import (
    BUSINESS_ID_ATTRIBUTE,
    find_operation_business_id,
)

# A queued job whose payload names another business than the job itself.
JOB_TENANT_MISMATCH: str = "job_tenant_mismatch"
JOB_TENANT_MISMATCH_REASON: str = "payload_names_other_business"


class BusinessScopedPipelineOperator[InputData, OutputData](
    OperatorContract[InputData, OutputData]
):
    """
    Endpoint operator that runs one pipeline synchronously inside the
    storage scope of the business its input names (concept sections 1, 2
    and 10: row-level security as the second line of defence). A request
    for business A then cannot read or write business B's tenant rows on
    Postgres even if a repository forgot its business filter. Inputs
    without a business (sign-in, the signed-in user's own account and
    business list) run in the caller's scope, by default unscoped: they may
    use platform collections (users, sessions, businesses) but no tenant
    collection (fail-closed). Platform-level work uses
    `PlatformWidePipelineOperator`; code that must look across businesses
    escalates explicitly with `StorageScopeContract.platform_wide()`. The
    business is also bound to the log context, so log lines and error
    reports of the operation name it.

    A queued job of one business whose payload names another business
    (`business_id` of the payload's JSON object) is refused before its
    handler runs, with a security log line: the job would run in one
    business's scope on another business's data (an in-memory store has no
    row-level security to stop it). The job queue retries it and keeps it
    as a dead letter.
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

        with bound_log_context(business_id=business_id):
            if isinstance(input_data, QueuedJobInput):
                refuse_foreign_payload(input_data, business_id)
            with self._storage_scope.scoped_to_business(business_id):
                return self._pipeline.start(input_data)


def refuse_foreign_payload(job: QueuedJobInput, business_id: BusinessId) -> None:
    """
    Raises:
        AccessDeniedError: the job's payload names another business (its
            JSON object's `business_id`); logged as a security event.
    """

    named: str | None = payload_business_reference(str(job.payload))
    if named is None or named == str(business_id):
        return

    log_security_event(
        JOB_TENANT_MISMATCH,
        path=f"queued_job:{job.job_name}",
        reason=JOB_TENANT_MISMATCH_REASON,
        client_address=None,
        job_id=str(job.job_id),
    )
    raise AccessDeniedError(
        f"Job {job.job_id} ({job.job_name}) was refused: its payload names "
        "another business than the job."
    )


def payload_business_reference(payload: str) -> str | None:
    """The `business_id` a job payload's JSON object names, as text, or None."""

    try:
        decoded: object = json.loads(payload)
    except ValueError:
        return None

    if not isinstance(decoded, dict):
        return None

    named: object = cast(dict[str, object], decoded).get(BUSINESS_ID_ATTRIBUTE)
    if named is None:
        return None

    return str(named)
