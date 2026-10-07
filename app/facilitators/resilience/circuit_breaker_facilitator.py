import logging
import threading
from collections import deque
from dataclasses import dataclass, field

from typed_time_provider import MonotonicClock, Nanoseconds

from app.contracts.resilience import CircuitBreakerContract
from app.contracts.service_metrics import ServiceMetricsContract
from app.schemas.constants.resilience import CircuitState
from app.schemas.dto.resilience import CircuitBreakerPolicy
from app.schemas.typings.resilience.constrained_strings import CircuitName
from app.utilities.observability.metrics.null_service_metrics import (
    NO_SERVICE_METRICS,
)

logger: logging.Logger = logging.getLogger(__name__)
NANOSECONDS_PER_SECOND: int = 1_000_000_000


@dataclass
class CircuitRecord:
    """The mutable state of one circuit (technical bookkeeping)."""

    state: CircuitState = CircuitState.CLOSED
    failures: deque[int] = field(default_factory=deque[int])
    opened_at: int = 0
    is_trial_running: bool = False


class CircuitBreakerFacilitator(CircuitBreakerContract):
    """
    In-process circuit breakers (one per circuit name), so a provider that
    keeps failing is not waited on by every customer: after
    `failure_threshold` failures within `window_seconds` the circuit opens
    and callers go elsewhere at once; after `open_seconds` one trial call
    goes through (half-open), and its success closes the circuit, its
    failure opens it again. Each process keeps its own breakers: a worker
    learns of an outage from its own calls within seconds. Thread-safe.
    Each state change goes to /metrics (the circuit breaker state gauge).
    """

    def __init__(
        self,
        monotonic_clock: MonotonicClock[Nanoseconds],
        policy: CircuitBreakerPolicy | None = None,
        metrics: ServiceMetricsContract = NO_SERVICE_METRICS,
    ) -> None:
        self._metrics: ServiceMetricsContract = metrics
        self._monotonic_clock: MonotonicClock[Nanoseconds] = monotonic_clock
        self._policy: CircuitBreakerPolicy = (
            CircuitBreakerPolicy() if policy is None else policy
        )
        self._lock: threading.Lock = threading.Lock()
        self._circuits: dict[CircuitName, CircuitRecord] = {}

    def allows_call(self, circuit: CircuitName) -> bool:
        now: int = self._now()
        with self._lock:
            record: CircuitRecord = self._record(circuit)
            if record.state is CircuitState.CLOSED:
                return True

            if record.state is CircuitState.OPEN:
                if now - record.opened_at < self._open_nanoseconds():
                    return False

                record.state = CircuitState.HALF_OPEN
                record.is_trial_running = False
                self._metrics.set_circuit_state(circuit, record.state)

            if record.is_trial_running:
                return False

            record.is_trial_running = True
            return True

    def record_success(self, circuit: CircuitName) -> None:
        with self._lock:
            record: CircuitRecord = self._record(circuit)
            if record.state is not CircuitState.CLOSED:
                logger.info("Circuit %s closed: its trial call succeeded.", circuit)
                self._metrics.set_circuit_state(circuit, CircuitState.CLOSED)

            record.state = CircuitState.CLOSED
            record.failures.clear()
            record.is_trial_running = False

    def record_failure(self, circuit: CircuitName) -> None:
        now: int = self._now()
        with self._lock:
            record: CircuitRecord = self._record(circuit)
            if record.state is CircuitState.HALF_OPEN:
                self._open(circuit, record, now, "its trial call failed")
                return

            if record.state is CircuitState.OPEN:
                return

            record.failures.append(now)
            window_start: int = now - int(self._policy.window_seconds) * (
                NANOSECONDS_PER_SECOND
            )
            while record.failures and record.failures[0] < window_start:
                record.failures.popleft()

            if len(record.failures) >= int(self._policy.failure_threshold):
                self._open(
                    circuit,
                    record,
                    now,
                    f"{len(record.failures)} failures within "
                    f"{int(self._policy.window_seconds)} s",
                )

    def state(self, circuit: CircuitName) -> CircuitState:
        with self._lock:
            return self._record(circuit).state

    def _open(
        self, circuit: CircuitName, record: CircuitRecord, now: int, reason: str
    ) -> None:
        record.state = CircuitState.OPEN
        record.opened_at = now
        record.failures.clear()
        record.is_trial_running = False
        self._metrics.set_circuit_state(circuit, record.state)
        logger.warning(
            "Circuit %s opened (%s); calls go elsewhere for %d s.",
            circuit,
            reason,
            int(self._policy.open_seconds),
        )

    def _record(self, circuit: CircuitName) -> CircuitRecord:
        record: CircuitRecord | None = self._circuits.get(circuit)
        if record is None:
            record = CircuitRecord()
            self._circuits[circuit] = record
            self._metrics.set_circuit_state(circuit, record.state)

        return record

    def _open_nanoseconds(self) -> int:
        return int(self._policy.open_seconds) * NANOSECONDS_PER_SECOND

    def _now(self) -> int:
        return int(self._monotonic_clock.now_monotonic())
