"""The breaker's state on /metrics: 0 closed, 1 half-open, 2 open."""

from prometheus_client import CollectorRegistry
from typed_time_provider import MonotonicClock, Nanoseconds

from app.facilitators.resilience.circuit_breaker_facilitator import (
    CircuitBreakerFacilitator,
)
from app.schemas.typings.resilience.constrained_strings import CircuitName
from app.utilities.observability.metrics.prometheus_service_metrics import (
    PrometheusServiceMetrics,
)

SECOND: int = 1_000_000_000
OPENAI: CircuitName = CircuitName("openai:gpt-5.5-mini")


class Ticks:
    def __init__(self) -> None:
        self.now: int = 1_000 * SECOND

    def clock(self) -> MonotonicClock[Nanoseconds]:
        return MonotonicClock(
            preferred_time_unit_type=Nanoseconds,
            monotonic_nanosecond_factory=lambda: self.now,
        )


def test_the_gauge_follows_the_circuit_through_open_half_open_and_closed() -> None:
    ticks, registry = Ticks(), CollectorRegistry()
    breaker = CircuitBreakerFacilitator(
        ticks.clock(), metrics=PrometheusServiceMetrics(registry)
    )

    def state() -> float | None:
        return registry.get_sample_value(
            "workshop_circuit_breaker_state", {"circuit": str(OPENAI)}
        )

    assert breaker.allows_call(OPENAI)
    closed = state()
    for _ in range(5):
        breaker.record_failure(OPENAI)
    opened = state()
    ticks.now += 3_600 * SECOND
    assert breaker.allows_call(OPENAI)
    half_open = state()
    breaker.record_success(OPENAI)

    assert (closed, opened, half_open, state()) == (0.0, 2.0, 1.0, 0.0)
