"""
A queued job carries the request that queued it: its log lines name that
request id, its span continues that request's trace, and the worker counts
its pickup and, when it dies, its death.
"""

import logging
from collections.abc import Iterator

import pytest
from opentelemetry.sdk.trace import ReadableSpan, TracerProvider
from opentelemetry.sdk.trace.export import SimpleSpanProcessor
from opentelemetry.sdk.trace.export.in_memory_span_exporter import (
    InMemorySpanExporter,
)
from opentelemetry.trace import SpanKind as OtelSpanKind
from prometheus_client import CollectorRegistry

from app.gateways.worker.job_telemetry import JobTelemetry
from app.schemas.constants.jobs import JobLane, QueuedJobStatus
from app.schemas.constants.telemetry import SpanKind
from app.schemas.domain.jobs import QueuedJobDocument
from app.schemas.dto.jobs import JobReport, QueuedJobInput
from app.schemas.typings.platform.constrained_integers import ProcessedItemCount
from app.schemas.typings.platform.constrained_strings import JobName, RequestId
from app.schemas.typings.platform.strings import JobPayloadJson
from app.utilities.observability.log_context import bound_log_context
from app.utilities.observability.log_formatting import (
    CONTEXT_FIELDS_ATTRIBUTE,
    LogContextFilter,
)
from app.utilities.observability.metrics.prometheus_service_metrics import (
    PrometheusServiceMetrics,
)
from app.utilities.observability.tracing.open_telemetry_span_tracer import (
    OpenTelemetrySpanTracer,
)
from tests.platform.worker_fakes import ControlledClock, build_worker

LOGGER_NAME: str = "app.tests.job_telemetry"
SEND_RECEIPT: JobName = JobName("send_receipt")
MISSING_HANDLER: JobName = JobName("retired_job")
CHECKOUT_REQUEST: RequestId = RequestId("req-checkout-0001")


class LoggingOperator:
    def operate(self, input_data: QueuedJobInput) -> JobReport:
        logging.getLogger(LOGGER_NAME).info("Sending the receipt")
        del input_data
        return JobReport(processed_count=ProcessedItemCount(1))


class CapturingHandler(logging.Handler):
    def __init__(self) -> None:
        super().__init__()
        self.addFilter(LogContextFilter())
        self.fields: list[dict[str, str]] = []

    def emit(self, record: logging.LogRecord) -> None:
        self.fields.append(dict(getattr(record, CONTEXT_FIELDS_ATTRIBUTE)))


@pytest.fixture
def captured() -> Iterator[CapturingHandler]:
    handler = CapturingHandler()
    logger = logging.getLogger(LOGGER_NAME)
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)
    yield handler
    logger.removeHandler(handler)


@pytest.fixture
def exporter() -> InMemorySpanExporter:
    return InMemorySpanExporter()


@pytest.fixture
def tracer(exporter: InMemorySpanExporter) -> Iterator[OpenTelemetrySpanTracer]:
    provider = TracerProvider()
    provider.add_span_processor(SimpleSpanProcessor(exporter))
    yield OpenTelemetrySpanTracer(provider.get_tracer("tests"))
    provider.shutdown()


def only_span(exporter: InMemorySpanExporter, name: str) -> ReadableSpan:
    [span] = [span for span in exporter.get_finished_spans() if span.name == name]
    return span


def test_a_jobs_log_lines_carry_the_request_id_that_queued_it(
    captured: CapturingHandler,
) -> None:
    kit = build_worker(ControlledClock(), [], {SEND_RECEIPT: LoggingOperator()})
    with bound_log_context(request_id=CHECKOUT_REQUEST):
        job_id = kit.queue.enqueue(SEND_RECEIPT, JobPayloadJson("{}"), None)

    report = kit.worker.run_queued_jobs()

    assert report.failures == 0
    stored: QueuedJobDocument | None = kit.job_repo.get(job_id)
    assert stored is not None
    assert stored.request_id == CHECKOUT_REQUEST
    [fields] = captured.fields
    assert fields["request_id"] == str(CHECKOUT_REQUEST)
    assert fields["job_name"] == str(SEND_RECEIPT)


def test_a_jobs_span_continues_the_trace_that_queued_it(
    exporter: InMemorySpanExporter,
    tracer: OpenTelemetrySpanTracer,
    captured: CapturingHandler,
) -> None:
    kit = build_worker(
        ControlledClock(),
        [],
        {SEND_RECEIPT: LoggingOperator()},
        job_telemetry=JobTelemetry(tracer=tracer),
    )
    with tracer.span("POST /v1/checkout", SpanKind.SERVER, {}):
        kit.queue.enqueue(
            SEND_RECEIPT, JobPayloadJson("{}"), None, lane=JobLane.OUTBOUND
        )

    assert kit.worker.run_queued_jobs().failures == 0

    request = only_span(exporter, "POST /v1/checkout")
    job = only_span(exporter, f"job {SEND_RECEIPT}")
    assert job.kind is OtelSpanKind.CONSUMER
    assert job.context is not None and request.context is not None
    assert job.context.trace_id == request.context.trace_id
    assert job.parent is not None
    assert job.parent.span_id == request.context.span_id
    assert job.attributes is not None
    assert job.attributes["workshop.job.lane"] == "outbound"
    [fields] = captured.fields
    assert fields["trace_id"] == format(request.context.trace_id, "032x")


def test_pickups_and_dead_jobs_are_counted() -> None:
    registry = CollectorRegistry()
    clock = ControlledClock()
    kit = build_worker(
        clock,
        [],
        {SEND_RECEIPT: LoggingOperator()},
        job_telemetry=JobTelemetry(metrics=PrometheusServiceMetrics(registry)),
    )
    kit.queue.enqueue(SEND_RECEIPT, JobPayloadJson("{}"), None)
    dead_id = kit.queue.enqueue(MISSING_HANDLER, JobPayloadJson("{}"), None)
    clock.advance(3)

    kit.worker.run_queued_jobs()

    dead: QueuedJobDocument | None = kit.job_repo.get(dead_id)
    assert dead is not None and dead.status is QueuedJobStatus.DEAD
    assert (
        registry.get_sample_value(
            "workshop_jobs_died_total", {"job": str(MISSING_HANDLER)}
        )
        == 1
    )
    assert (
        registry.get_sample_value(
            "workshop_jobs_died_total", {"job": str(SEND_RECEIPT)}
        )
        is None
    )
    assert (
        registry.get_sample_value(
            "workshop_job_pickup_delay_seconds_count", {"lane": "default"}
        )
        == 2
    )
    assert (
        registry.get_sample_value(
            "workshop_job_pickup_delay_seconds_sum", {"lane": "default"}
        )
        == 6.0
    )
