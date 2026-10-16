"""
What the worker tells about the queued jobs it runs, besides its log
lines: the pickup delay and the jobs that died (Prometheus), and one span
per run that continues the trace of the code that queued the job. While a
job runs, its log lines carry the request id of what queued it and the id
of its trace, so a webhook's lines and its job's lines are found together.
"""

from collections.abc import Generator
from contextlib import contextmanager

from typed_time_provider import Microseconds

from app.contracts.service_metrics import ServiceMetricsContract
from app.gateways.worker.job_run_logs import log_pickup
from app.schemas.constants.jobs import QueuedJobStatus
from app.schemas.constants.telemetry import SpanKind
from app.schemas.domain.jobs import QueuedJobDocument
from app.utilities.observability.log_context import bound_log_context
from app.utilities.observability.metrics.null_service_metrics import (
    NO_SERVICE_METRICS,
)
from app.utilities.observability.metrics.observed_durations import (
    seconds_between_microseconds,
)
from app.utilities.observability.tracing.span_tracer import (
    NO_SPAN_TRACER,
    SpanHandle,
    SpanTracer,
)
from app.utilities.observability.tracing.trace_context import current_trace_id

JOB_SPAN_OPERATION: str = "queue.process"


class JobTelemetry:
    """Metrics, spans and log context of the queued jobs of one worker."""

    def __init__(
        self,
        metrics: ServiceMetricsContract = NO_SERVICE_METRICS,
        tracer: SpanTracer = NO_SPAN_TRACER,
    ) -> None:
        self._metrics: ServiceMetricsContract = metrics
        self._tracer: SpanTracer = tracer

    def picked_up(self, job: QueuedJobDocument, claimed_at: Microseconds) -> None:
        """A claimed job: its log line and how long it waited after due."""

        log_pickup(job, claimed_at)
        self._metrics.observe_job_pickup(
            job.lane, seconds_between_microseconds(int(job.run_at), int(claimed_at))
        )

    @contextmanager
    def running(self, job: QueuedJobDocument) -> Generator[SpanHandle]:
        """
        The block that runs one job: its log context (the job, its business,
        the request that queued it) and its span in the queuing trace.
        """

        with (
            bound_log_context(
                job_name=job.name,
                job_id=job.id,
                business_id=job.business_id,
                request_id=job.request_id,
            ),
            self._tracer.span(
                f"job {job.name}",
                SpanKind.CONSUMER,
                {
                    "messaging.operation.type": "process",
                    "workshop.job.name": str(job.name),
                    "workshop.job.lane": job.lane.value,
                    "workshop.job.attempt": int(job.attempts),
                    "sentry.op": JOB_SPAN_OPERATION,
                },
                parent=job.trace_parent,
            ) as span,
            bound_log_context(trace_id=current_trace_id()),
        ):
            yield span

    def settled(self, job: QueuedJobDocument) -> None:
        """A job whose run or reaping left it DEAD counts as a dead job."""

        if job.status is QueuedJobStatus.DEAD:
            self._metrics.count_dead_job(job.name)


NO_JOB_TELEMETRY: JobTelemetry = JobTelemetry()
