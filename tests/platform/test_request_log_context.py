"""Log lines and error reports of a request or a job name what they were about."""

import logging
from collections.abc import Iterator
from dataclasses import dataclass

import pytest
from fastapi import APIRouter
from fastapi.testclient import TestClient

from app.gateways.http.application import build_http_application
from app.operators.business_scoped_pipeline_operator import (
    BusinessScopedPipelineOperator,
)
from app.schemas.dto.jobs import JobReport, QueuedJobInput
from app.schemas.dto.observability import LogContext
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.platform.constrained_integers import ProcessedItemCount
from app.schemas.typings.platform.strings import JobPayloadJson
from app.utilities.observability.log_context import (
    current_log_context,
    log_context_of_error,
)
from app.utilities.observability.log_formatting import (
    CONTEXT_FIELDS_ATTRIBUTE,
    LogContextFilter,
)
from app.utilities.storage.storage_scope_context import StorageScopeContext
from tests.platform.worker_fakes import RUN_AUTOTESTS, ControlledClock, build_worker

LOGGER_NAME: str = "app.tests.request_logs"
BUSINESS_ID: BusinessId = BusinessId("business_0f8f6bd6-e9b2-4a4c-8b8c-3c1f2a7e9d10")


@dataclass(frozen=True)
class BusinessQuery:
    business_id: BusinessId
    should_fail: bool = False


class LoggingPipeline:
    def start(self, input_data: BusinessQuery) -> dict[str, str]:
        logging.getLogger(LOGGER_NAME).warning("Reading the business")
        if input_data.should_fail:
            raise RuntimeError("database exploded")

        return {"status": "ok"}


class CapturingHandler(logging.Handler):
    def __init__(self) -> None:
        super().__init__()
        self.addFilter(LogContextFilter())
        self.records: list[logging.LogRecord] = []

    def emit(self, record: logging.LogRecord) -> None:
        self.records.append(record)


class ContextRecordingReporter:
    def __init__(self) -> None:
        self.contexts: list[LogContext] = []

    def capture_exception(self, error: BaseException) -> None:
        self.contexts.append(log_context_of_error(error))


@pytest.fixture
def captured() -> Iterator[CapturingHandler]:
    handler = CapturingHandler()
    logger = logging.getLogger(LOGGER_NAME)
    logger.addHandler(handler)
    yield handler
    logger.removeHandler(handler)


def build_client(reporter: ContextRecordingReporter) -> TestClient:
    operator = BusinessScopedPipelineOperator[BusinessQuery, dict[str, str]](
        LoggingPipeline(), StorageScopeContext()
    )
    router = APIRouter()

    @router.get("/businesses/{business_id}")
    def read_business(business_id: str, fail: bool = False) -> dict[str, str]:
        return operator.operate(BusinessQuery(BusinessId(business_id), fail))

    application = build_http_application(
        routers=[router], error_reporter=reporter, cors_allowed_origins=[]
    )
    return TestClient(application, raise_server_exceptions=False)


def test_log_lines_inside_a_request_carry_the_request_and_business(
    captured: CapturingHandler,
) -> None:
    client = build_client(ContextRecordingReporter())

    response = client.get(
        f"/businesses/{BUSINESS_ID}", headers={"X-Request-ID": "req-77"}
    )

    assert response.status_code == 200
    assert response.headers["X-Request-ID"] == "req-77"
    [record] = captured.records
    assert getattr(record, CONTEXT_FIELDS_ATTRIBUTE) == {
        "request_id": "req-77",
        "business_id": str(BUSINESS_ID),
    }
    # Nothing leaks into the code that runs after the request.
    assert current_log_context() == LogContext()


def test_an_unexpected_error_is_reported_with_its_request_and_business(
    captured: CapturingHandler,
) -> None:
    reporter = ContextRecordingReporter()
    client = build_client(reporter)

    response = client.get(
        f"/businesses/{BUSINESS_ID}?fail=true", headers={"X-Request-ID": "req-500"}
    )

    assert response.status_code == 500
    assert response.headers["X-Request-ID"] == "req-500"
    assert [context.as_fields() for context in reporter.contexts] == [
        {"request_id": "req-500", "business_id": str(BUSINESS_ID)}
    ]
    assert len(captured.records) == 1


def test_a_queued_job_runs_with_its_job_and_business_in_the_context() -> None:
    seen: list[LogContext] = []

    class ContextOperator:
        def operate(self, input_data: QueuedJobInput) -> JobReport:
            del input_data
            seen.append(current_log_context())
            return JobReport(processed_count=ProcessedItemCount(1))

    kit = build_worker(ControlledClock(), [], {RUN_AUTOTESTS: ContextOperator()})
    job_id = kit.queue.enqueue(
        RUN_AUTOTESTS, JobPayloadJson("{}"), business_id=BUSINESS_ID
    )

    kit.worker.run_queued_jobs()

    assert [context.as_fields() for context in seen] == [
        {
            "business_id": str(BUSINESS_ID),
            "job_name": "run_autotests",
            "job_id": str(job_id),
        }
    ]
    assert current_log_context() == LogContext()
