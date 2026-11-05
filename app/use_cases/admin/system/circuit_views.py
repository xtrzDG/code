"""How the admin system page shows the workers' circuit breakers."""

from collections.abc import Sequence
from dataclasses import dataclass, field

from typed_time_provider import Microseconds

from app.schemas.constants.resilience import CircuitState
from app.schemas.domain.jobs import WorkerCircuitState, WorkerHeartbeatDocument
from app.schemas.dto.admin_system import CircuitSummaryView, WorkerCircuitView
from app.schemas.typings.resilience.constrained_integers import (
    CircuitFailureCount,
    CircuitWorkerCount,
)
from app.schemas.typings.resilience.constrained_strings import CircuitName
from app.use_cases.admin.alerts.stale_workers import is_pulse_stale

# The worst first: an open circuit refuses calls, a half-open one tries one.
STATE_ORDER: tuple[CircuitState, ...] = (
    CircuitState.OPEN,
    CircuitState.HALF_OPEN,
    CircuitState.CLOSED,
)
MAX_FAILURES_SHOWN: int = 1000


@dataclass
class CircuitTally:
    """One circuit's reports across the live workers (bookkeeping)."""

    states: list[CircuitState] = field(default_factory=list[CircuitState])
    failures: int = 0
    opened_at: list[int] = field(default_factory=list[int])


def worker_circuit_view(circuit: WorkerCircuitState) -> WorkerCircuitView:
    return WorkerCircuitView(
        circuit=circuit.circuit,
        state=circuit.state,
        recent_failures=circuit.recent_failures,
        opened_at=circuit.opened_at,
    )


def circuit_summaries(
    pulses: Sequence[WorkerHeartbeatDocument],
    now: Microseconds,
) -> list[CircuitSummaryView]:
    """
    Every circuit the live workers report, the circuits that are not closed
    first (open before half-open), then by name. A stale pulse says nothing
    about how a provider is doing now and is left out.
    """

    tallies: dict[CircuitName, CircuitTally] = {}
    for pulse in pulses:
        if is_pulse_stale(pulse, now):
            continue

        for circuit in pulse.circuits:
            tally: CircuitTally = tallies.setdefault(circuit.circuit, CircuitTally())
            tally.states.append(circuit.state)
            tally.failures += int(circuit.recent_failures)
            if circuit.opened_at is not None:
                tally.opened_at.append(int(circuit.opened_at))

    summaries: list[CircuitSummaryView] = [
        summary_view(circuit, tally) for circuit, tally in tallies.items()
    ]
    return sorted(
        summaries,
        key=lambda view: (STATE_ORDER.index(view.state), str(view.circuit)),
    )


def summary_view(circuit: CircuitName, tally: CircuitTally) -> CircuitSummaryView:
    worst: CircuitState = min(tally.states, key=STATE_ORDER.index)
    return CircuitSummaryView(
        circuit=circuit,
        state=worst,
        workers_not_closed=CircuitWorkerCount(
            sum(1 for state in tally.states if state is not CircuitState.CLOSED)
        ),
        workers_reporting=CircuitWorkerCount(len(tally.states)),
        recent_failures=CircuitFailureCount(min(tally.failures, MAX_FAILURES_SHOWN)),
        opened_at=(None if not tally.opened_at else Microseconds(min(tally.opened_at))),
    )
