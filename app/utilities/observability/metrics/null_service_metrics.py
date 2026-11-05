from app.contracts.service_metrics import ServiceMetricsContract
from app.schemas.constants.channels import ChannelKind
from app.schemas.constants.jobs import JobLane
from app.schemas.constants.resilience import CircuitState
from app.schemas.constants.telemetry import (
    OutboundAttemptOutcome,
    WebhookMessageOutcome,
)
from app.schemas.dto.telemetry import HttpRequestObservation, LlmCallObservation
from app.schemas.typings.channels.constrained_integers import WebhookMessageCount
from app.schemas.typings.observability.constrained_floats import ObservedSeconds
from app.schemas.typings.observability.constrained_strings import MetricsLabel
from app.schemas.typings.platform.constrained_strings import JobName
from app.schemas.typings.resilience.constrained_strings import CircuitName


class NullServiceMetrics(ServiceMetricsContract):
    """Observes nothing: the default of code built without metrics (tests)."""

    def observe_http_request(self, observation: HttpRequestObservation) -> None:
        del observation

    def count_webhook_messages(
        self,
        channel: ChannelKind,
        outcome: WebhookMessageOutcome,
        count: WebhookMessageCount,
    ) -> None:
        del channel, outcome, count

    def observe_job_pickup(self, lane: JobLane, delay: ObservedSeconds) -> None:
        del lane, delay

    def count_dead_job(self, job_name: JobName) -> None:
        del job_name

    def observe_answer_latency(
        self, channel: ChannelKind, latency: ObservedSeconds
    ) -> None:
        del channel, latency

    def count_outbound_attempt(
        self, provider: MetricsLabel, outcome: OutboundAttemptOutcome
    ) -> None:
        del provider, outcome

    def observe_llm_call(self, observation: LlmCallObservation) -> None:
        del observation

    def observe_pool_wait(self, wait: ObservedSeconds) -> None:
        del wait

    def count_pool_connection_taken(self) -> None:
        return

    def count_pool_connection_returned(self) -> None:
        return

    def set_circuit_state(self, circuit: CircuitName, state: CircuitState) -> None:
        del circuit, state


NO_SERVICE_METRICS: ServiceMetricsContract = NullServiceMetrics()
