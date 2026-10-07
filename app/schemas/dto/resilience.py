"""Circuit breakers: when a failing dependency is left alone for a while."""

from base_pydantic_schemas import ImmutableDTO

from app.schemas.typings.resilience.constrained_integers import (
    CircuitFailureThreshold,
    CircuitOpenSeconds,
    CircuitWindowSeconds,
)


class CircuitBreakerPolicy(ImmutableDTO):
    """
    A circuit opens after `failure_threshold` failures within
    `window_seconds` and refuses calls for `open_seconds`; then one trial
    call decides. The language-model default: 5 failures in 60 s, a trial
    after 30 s.
    """

    failure_threshold: CircuitFailureThreshold = CircuitFailureThreshold(5)
    window_seconds: CircuitWindowSeconds = CircuitWindowSeconds(60)
    open_seconds: CircuitOpenSeconds = CircuitOpenSeconds(30)
