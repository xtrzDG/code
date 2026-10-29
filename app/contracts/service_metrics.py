"""
The service metrics every process keeps for Prometheus (GET /metrics of
the API, WORKER_METRICS_PORT of a worker): what the code observed, never
ids, texts or addresses, so the number of series stays bounded.
"""

from typing import Protocol

from app.contracts.base_contract import BaseContract
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


class ServiceMetricsContract(BaseContract, Protocol):
    """Every method is cheap and never raises: metrics never fail the work."""

    def observe_http_request(self, observation: HttpRequestObservation) -> None:
        """One answered HTTP request: its duration by route and status class."""
        raise NotImplementedError

    def count_webhook_messages(
        self,
        channel: ChannelKind,
        outcome: WebhookMessageOutcome,
        count: WebhookMessageCount,
    ) -> None:
        raise NotImplementedError

    def observe_job_pickup(self, lane: JobLane, delay: ObservedSeconds) -> None:
        """How long a due job waited for a worker of its lane."""
        raise NotImplementedError

    def count_dead_job(self, job_name: JobName) -> None:
        """A queued job ran out of attempts or took its worker down twice."""
        raise NotImplementedError

    def observe_answer_latency(
        self, channel: ChannelKind, latency: ObservedSeconds
    ) -> None:
        """From a customer's first unanswered message to the stored reply."""
        raise NotImplementedError

    def count_outbound_attempt(
        self, provider: MetricsLabel, outcome: OutboundAttemptOutcome
    ) -> None:
        raise NotImplementedError

    def observe_llm_call(self, observation: LlmCallObservation) -> None:
        raise NotImplementedError

    def observe_pool_wait(self, wait: ObservedSeconds) -> None:
        """How long a thread waited for a database connection of the pool."""
        raise NotImplementedError

    def count_pool_connection_taken(self) -> None:
        """A connection of the pool was handed out (in use until returned)."""
        raise NotImplementedError

    def count_pool_connection_returned(self) -> None:
        raise NotImplementedError

    def set_circuit_state(self, circuit: CircuitName, state: CircuitState) -> None:
        raise NotImplementedError
