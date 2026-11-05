"""
The service metrics in Prometheus series (prometheus_client), on the
registry of one application container. Names and labels are documented in
docs/operations/observability.md; labels hold route templates, channels,
lanes, providers, models and job names only.
"""

from prometheus_client import CollectorRegistry, Counter, Gauge, Histogram

from app.contracts.service_metrics import ServiceMetricsContract
from app.schemas.constants.channels import ChannelKind
from app.schemas.constants.jobs import JobLane
from app.schemas.constants.resilience import CircuitState
from app.schemas.constants.telemetry import (
    LlmCallOutcome,
    OutboundAttemptOutcome,
    WebhookMessageOutcome,
)
from app.schemas.dto.telemetry import HttpRequestObservation, LlmCallObservation
from app.schemas.typings.channels.constrained_integers import WebhookMessageCount
from app.schemas.typings.observability.constrained_floats import ObservedSeconds
from app.schemas.typings.observability.constrained_strings import MetricsLabel
from app.schemas.typings.platform.constrained_strings import JobName
from app.schemas.typings.resilience.constrained_strings import CircuitName

HTTP_BUCKETS: tuple[float, ...] = (
    0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0, 30.0,
)  # fmt: skip
PICKUP_BUCKETS: tuple[float, ...] = (
    0.05, 0.1, 0.25, 0.5, 1.0, 2.0, 5.0, 10.0, 30.0, 60.0, 120.0, 300.0, 900.0,
)  # fmt: skip
# The answer SLO is 60 s (answered in time) and 15 s at p95 (latency).
ANSWER_BUCKETS: tuple[float, ...] = (
    1.0, 2.0, 3.0, 5.0, 8.0, 10.0, 15.0, 20.0, 30.0, 45.0, 60.0, 120.0, 300.0,
)  # fmt: skip
LLM_BUCKETS: tuple[float, ...] = (
    0.25, 0.5, 1.0, 2.0, 3.0, 5.0, 8.0, 12.0, 20.0, 30.0, 60.0,
)  # fmt: skip
POOL_WAIT_BUCKETS: tuple[float, ...] = (
    0.001, 0.005, 0.01, 0.05, 0.1, 0.5, 1.0, 5.0, 10.0, 30.0,
)  # fmt: skip
# The circuit's state as a number, for graphs and `max` across processes.
CIRCUIT_STATE_VALUES: dict[CircuitState, float] = {
    CircuitState.CLOSED: 0.0,
    CircuitState.HALF_OPEN: 1.0,
    CircuitState.OPEN: 2.0,
}
RATE_LIMITED_STATUS: int = 429


class PrometheusServiceMetrics(ServiceMetricsContract):
    """
    One process's series. With PROMETHEUS_MULTIPROC_DIR the values live in
    files there (prometheus_client's multiprocess mode) and /metrics adds
    up the processes; gauges then take the sum (connections in use) or the
    worst (circuit state) of the processes alive.
    """

    def __init__(self, registry: CollectorRegistry) -> None:
        self._http_duration = Histogram(
            "workshop_http_request_duration_seconds",
            "HTTP requests by route template and status class, and their time.",
            ["method", "route", "status_class"],
            buckets=HTTP_BUCKETS,
            registry=registry,
        )
        self._rate_limited = Counter(
            "workshop_rate_limit_rejections",
            "Requests refused with 429 by a rate limit, by route template.",
            ["route"],
            registry=registry,
        )
        self._webhook_messages = Counter(
            "workshop_webhook_messages",
            "Customer messages webhooks brought: received, queued, duplicate.",
            ["channel", "outcome"],
            registry=registry,
        )
        self._pickup = Histogram(
            "workshop_job_pickup_delay_seconds",
            "How long due jobs waited for a worker, by lane.",
            ["lane"],
            buckets=PICKUP_BUCKETS,
            registry=registry,
        )
        self._dead_jobs = Counter(
            "workshop_jobs_died",
            "Queued jobs that ran out of attempts or killed their worker twice.",
            ["job"],
            registry=registry,
        )
        self._answer = Histogram(
            "workshop_answer_latency_seconds",
            "From a customer's first unanswered message to the stored reply.",
            ["channel"],
            buckets=ANSWER_BUCKETS,
            registry=registry,
        )
        self._outbound = Counter(
            "workshop_outbound_attempts",
            "Send attempts of outbox messages by provider and outcome.",
            ["provider", "outcome"],
            registry=registry,
        )
        self._llm_duration = Histogram(
            "workshop_llm_call_duration_seconds",
            "Language-model calls by provider, model and outcome.",
            ["provider", "model", "outcome"],
            buckets=LLM_BUCKETS,
            registry=registry,
        )
        self._llm_tokens = Counter(
            "workshop_llm_tokens",
            "Tokens of language-model calls by provider, model and direction.",
            ["provider", "model", "direction"],
            registry=registry,
        )
        self._pool_wait = Histogram(
            "workshop_db_pool_wait_seconds",
            "How long threads waited for a database connection of the pool.",
            buckets=POOL_WAIT_BUCKETS,
            registry=registry,
        )
        self._pool_in_use = Gauge(
            "workshop_db_pool_connections_in_use",
            "Database connections of the pool handed out right now.",
            registry=registry,
            multiprocess_mode="livesum",
        )
        self._circuit_state = Gauge(
            "workshop_circuit_breaker_state",
            "Circuit breaker state: 0 closed, 1 half-open, 2 open.",
            ["circuit"],
            registry=registry,
            multiprocess_mode="livemax",
        )

    def observe_http_request(self, observation: HttpRequestObservation) -> None:
        status: int = int(observation.status_code)
        self._http_duration.labels(
            method=str(observation.method),
            route=str(observation.route),
            status_class=f"{status // 100}xx",
        ).observe(float(observation.duration))
        if status == RATE_LIMITED_STATUS:
            self._rate_limited.labels(route=str(observation.route)).inc()

    def count_webhook_messages(
        self,
        channel: ChannelKind,
        outcome: WebhookMessageOutcome,
        count: WebhookMessageCount,
    ) -> None:
        if int(count) > 0:
            self._webhook_messages.labels(
                channel=channel.value, outcome=outcome.value
            ).inc(int(count))

    def observe_job_pickup(self, lane: JobLane, delay: ObservedSeconds) -> None:
        self._pickup.labels(lane=lane.value).observe(float(delay))

    def count_dead_job(self, job_name: JobName) -> None:
        self._dead_jobs.labels(job=str(job_name)).inc()

    def observe_answer_latency(
        self, channel: ChannelKind, latency: ObservedSeconds
    ) -> None:
        self._answer.labels(channel=channel.value).observe(float(latency))

    def count_outbound_attempt(
        self, provider: MetricsLabel, outcome: OutboundAttemptOutcome
    ) -> None:
        self._outbound.labels(provider=str(provider), outcome=outcome.value).inc()

    def observe_llm_call(self, observation: LlmCallObservation) -> None:
        provider: str = observation.provider.value
        model: str = str(observation.model_id)
        self._llm_duration.labels(
            provider=provider, model=model, outcome=observation.outcome.value
        ).observe(float(observation.duration))
        if observation.outcome is not LlmCallOutcome.OK:
            return

        for direction, tokens in (
            ("input", int(observation.input_tokens)),
            ("output", int(observation.output_tokens)),
        ):
            if tokens > 0:
                self._llm_tokens.labels(
                    provider=provider, model=model, direction=direction
                ).inc(tokens)

    def observe_pool_wait(self, wait: ObservedSeconds) -> None:
        self._pool_wait.observe(float(wait))

    def count_pool_connection_taken(self) -> None:
        self._pool_in_use.inc()

    def count_pool_connection_returned(self) -> None:
        self._pool_in_use.dec()

    def set_circuit_state(self, circuit: CircuitName, state: CircuitState) -> None:
        self._circuit_state.labels(circuit=str(circuit)).set(
            CIRCUIT_STATE_VALUES[state]
        )
