"""Circuit breakers: when a failing dependency is left alone for a while."""

from base_pydantic_schemas import ImmutableDTO

from app.schemas.constants.resilience import CircuitState
from app.schemas.typings.resilience.constrained_integers import (
    CircuitFailureCount,
    CircuitFailureThreshold,
    CircuitOpenAgeSeconds,
    CircuitOpenSeconds,
    CircuitWindowSeconds,
)
from app.schemas.typings.resilience.constrained_strings import CircuitName


class CircuitBreakerPolicy(ImmutableDTO):
    """
    A circuit opens after `failure_threshold` failures within
    `window_seconds` and refuses calls for `open_seconds`; then one trial
    call decides. The default (language models and the providers the
    platform sends through): 5 failures in 60 s, a trial after 30 s.
    """

    failure_threshold: CircuitFailureThreshold = CircuitFailureThreshold(5)
    window_seconds: CircuitWindowSeconds = CircuitWindowSeconds(60)
    open_seconds: CircuitOpenSeconds = CircuitOpenSeconds(30)


class CircuitSnapshot(ImmutableDTO):
    """
    One circuit of this process as it stands: its state, the failures a
    closed circuit counted within its window, and how long ago a circuit
    that is not closed opened (None while closed).
    """

    circuit: CircuitName
    state: CircuitState
    recent_failures: CircuitFailureCount = CircuitFailureCount(0)
    open_for_seconds: CircuitOpenAgeSeconds | None = None
