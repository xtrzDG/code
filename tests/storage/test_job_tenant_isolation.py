"""
A queued job of one business never runs on another business's data: the
business-scoped operator refuses a job whose payload names another
business than the job, before the handler runs, with a security log line.
"""

import json
import logging

import pytest

from app.contracts.pipeline_contract import PipelineContract
from app.operators.business_scoped_pipeline_operator import (
    JOB_TENANT_MISMATCH,
    BusinessScopedPipelineOperator,
    payload_business_reference,
)
from app.schemas.dto.jobs import JobReport, QueuedJobInput
from app.schemas.dto.storage import StorageScope
from app.schemas.exceptions.application_errors import AccessDeniedError
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.platform.constrained_strings import JobName
from app.schemas.typings.platform.prefixed_id import QueuedJobId
from app.schemas.typings.platform.strings import JobPayloadJson
from app.utilities.observability.log_formatting import read_line_fields
from app.utilities.storage.storage_scope_context import StorageScopeContext


class RecordingJobPipeline(PipelineContract[QueuedJobInput, JobReport]):
    """Remembers the scopes its jobs ran in."""

    def __init__(self, storage_scope: StorageScopeContext) -> None:
        self._storage_scope: StorageScopeContext = storage_scope
        self.scopes: list[StorageScope] = []

    def start(self, input_data: QueuedJobInput) -> JobReport:
        self.scopes.append(self._storage_scope.current())
        return JobReport()


def job_of(
    business_id: BusinessId | None, payload: dict[str, object]
) -> QueuedJobInput:
    return QueuedJobInput(
        job_id=QueuedJobId(),
        job_name=JobName("summarize_conversation"),
        payload=JobPayloadJson(json.dumps(payload)),
        business_id=business_id,
    )


def build_operator() -> tuple[
    BusinessScopedPipelineOperator[QueuedJobInput, JobReport], RecordingJobPipeline
]:
    storage_scope = StorageScopeContext()
    pipeline = RecordingJobPipeline(storage_scope)
    return BusinessScopedPipelineOperator(pipeline, storage_scope), pipeline


def test_a_job_naming_its_own_business_runs_in_its_scope() -> None:
    operator, pipeline = build_operator()
    business_id = BusinessId()

    operator.operate(job_of(business_id, {"business_id": str(business_id)}))
    operator.operate(job_of(business_id, {"conversation_id": "conv_1"}))

    assert pipeline.scopes == [StorageScope.for_business(business_id)] * 2


def test_a_job_whose_payload_names_another_business_is_refused_and_logged(
    caplog: pytest.LogCaptureFixture,
) -> None:
    operator, pipeline = build_operator()
    job = job_of(BusinessId(), {"business_id": str(BusinessId()), "x": 1})

    with (
        caplog.at_level(logging.WARNING, logger="app.security"),
        pytest.raises(AccessDeniedError, match="another business"),
    ):
        operator.operate(job)

    assert pipeline.scopes == []
    [line] = [record for record in caplog.records if record.name == "app.security"]
    fields: dict[str, object] = read_line_fields(line)
    assert fields["security_event"] == JOB_TENANT_MISMATCH
    assert fields["path"] == "queued_job:summarize_conversation"
    assert fields["job_id"] == str(job.job_id)


def test_a_platform_job_without_a_business_is_left_to_its_handler() -> None:
    operator, pipeline = build_operator()

    operator.operate(job_of(None, {"business_id": str(BusinessId())}))

    assert pipeline.scopes == [StorageScope.unscoped()]


@pytest.mark.parametrize(
    ("payload", "expected"),
    [
        ('{"business_id": "biz_1"}', "biz_1"),
        ('{"event_id": "evt_1"}', None),
        ("[1, 2]", None),
        ("not json", None),
        ('{"business_id": null}', None),
    ],
)
def test_the_named_business_is_read_from_the_payload_object(
    payload: str, expected: str | None
) -> None:
    assert payload_business_reference(payload) == expected
