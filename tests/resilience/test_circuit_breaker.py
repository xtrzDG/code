"""The circuit breaker in front of each language model."""

import threading

from typed_time_provider import MonotonicClock, Nanoseconds

from app.facilitators.resilience.circuit_breaker_facilitator import (
    CircuitBreakerFacilitator,
)
from app.schemas.constants.resilience import CircuitState
from app.schemas.typings.resilience.constrained_strings import CircuitName

SECOND: int = 1_000_000_000
OPENAI: CircuitName = CircuitName("openai:gpt-5-mini")
ANTHROPIC: CircuitName = CircuitName("anthropic:claude-sonnet-5-5")


class Ticks:
    """A monotonic clock the test moves."""

    def __init__(self) -> None:
        self.now: int = 1_000 * SECOND

    def clock(self) -> MonotonicClock[Nanoseconds]:
        return MonotonicClock(
            preferred_time_unit_type=Nanoseconds,
            monotonic_nanosecond_factory=lambda: self.now,
        )

    def advance(self, seconds: float) -> None:
        self.now += int(seconds * SECOND)


def breaker(ticks: Ticks) -> CircuitBreakerFacilitator:
    return CircuitBreakerFacilitator(ticks.clock())


def fail(circuit_breaker: CircuitBreakerFacilitator, times: int) -> None:
    for _ in range(times):
        circuit_breaker.record_failure(OPENAI)


def test_a_circuit_opens_after_five_failures_within_a_minute() -> None:
    ticks = Ticks()
    circuit_breaker = breaker(ticks)

    fail(circuit_breaker, 4)
    assert circuit_breaker.allows_call(OPENAI)
    assert circuit_breaker.state(OPENAI) is CircuitState.CLOSED

    ticks.advance(59)
    fail(circuit_breaker, 1)

    assert circuit_breaker.state(OPENAI) is CircuitState.OPEN
    assert not circuit_breaker.allows_call(OPENAI)
    # Another model has its own circuit.
    assert circuit_breaker.allows_call(ANTHROPIC)


def test_failures_older_than_the_window_do_not_count() -> None:
    ticks = Ticks()
    circuit_breaker = breaker(ticks)

    fail(circuit_breaker, 4)
    ticks.advance(61)
    fail(circuit_breaker, 4)

    assert circuit_breaker.state(OPENAI) is CircuitState.CLOSED
    assert circuit_breaker.allows_call(OPENAI)


def test_a_success_forgets_earlier_failures() -> None:
    ticks = Ticks()
    circuit_breaker = breaker(ticks)

    fail(circuit_breaker, 4)
    circuit_breaker.record_success(OPENAI)
    fail(circuit_breaker, 4)

    assert circuit_breaker.state(OPENAI) is CircuitState.CLOSED


def test_an_open_circuit_lets_one_trial_through_after_thirty_seconds() -> None:
    ticks = Ticks()
    circuit_breaker = breaker(ticks)
    fail(circuit_breaker, 5)

    ticks.advance(29)
    assert not circuit_breaker.allows_call(OPENAI)

    ticks.advance(1)
    assert circuit_breaker.allows_call(OPENAI)
    assert circuit_breaker.state(OPENAI) is CircuitState.HALF_OPEN
    # Only one trial at a time.
    assert not circuit_breaker.allows_call(OPENAI)

    circuit_breaker.record_success(OPENAI)

    assert circuit_breaker.state(OPENAI) is CircuitState.CLOSED
    assert circuit_breaker.allows_call(OPENAI)


def test_a_failed_trial_opens_the_circuit_for_another_wait() -> None:
    ticks = Ticks()
    circuit_breaker = breaker(ticks)
    fail(circuit_breaker, 5)
    ticks.advance(30)
    assert circuit_breaker.allows_call(OPENAI)

    circuit_breaker.record_failure(OPENAI)

    assert circuit_breaker.state(OPENAI) is CircuitState.OPEN
    ticks.advance(29)
    assert not circuit_breaker.allows_call(OPENAI)
    ticks.advance(1)
    assert circuit_breaker.allows_call(OPENAI)


def test_failures_of_an_open_circuit_do_not_extend_its_wait() -> None:
    ticks = Ticks()
    circuit_breaker = breaker(ticks)
    fail(circuit_breaker, 5)

    ticks.advance(20)
    fail(circuit_breaker, 3)
    ticks.advance(10)

    assert circuit_breaker.allows_call(OPENAI)


def test_threads_share_one_breaker() -> None:
    ticks = Ticks()
    circuit_breaker = breaker(ticks)

    threads = [
        threading.Thread(target=fail, args=(circuit_breaker, 1)) for _ in range(5)
    ]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()

    assert circuit_breaker.state(OPENAI) is CircuitState.OPEN
