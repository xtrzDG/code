"""
GET /v1/admin/system shows each worker's circuit breakers from its last
pulse, and sums every circuit up across the live workers: the circuits that
are not closed first, a stale pulse left out.
"""

from typed_time_provider import Microseconds

from app.schemas.constants.resilience import CircuitState
from app.schemas.domain.jobs import WorkerCircuitState, WorkerHeartbeatDocument
from app.schemas.dto.admin_system import AdminSystemQuery
from app.schemas.typings.resilience.constrained_integers import (
    CircuitFailureCount,
    CircuitWorkerCount,
)
from app.schemas.typings.resilience.constrained_strings import CircuitName
from app.use_cases.admin.system.circuit_views import circuit_summaries
from tests.platform_ops.ops_documents import HOUR, MINUTE, NOW, at, pulse
from tests.platform_ops.ops_world import ADMIN, OpsWorld, put
from tests.platform_ops.test_admin_system_view import system_page

META: CircuitName = CircuitName("provider:meta")
TELEGRAM: CircuitName = CircuitName("provider:telegram")
SMTP: CircuitName = CircuitName("provider:smtp")


def circuit(
    name: CircuitName,
    state: CircuitState,
    failures: int = 0,
    opened_at: Microseconds | None = None,
) -> WorkerCircuitState:
    return WorkerCircuitState(
        circuit=name,
        state=state,
        recent_failures=CircuitFailureCount(failures),
        opened_at=opened_at,
    )


def pulse_with(
    host: str, beat_at: Microseconds, *circuits: WorkerCircuitState
) -> WorkerHeartbeatDocument:
    return pulse(host, beat_at).model_copy(update={"circuits": list(circuits)})


def test_each_worker_shows_its_circuits_and_the_page_sums_them_up() -> None:
    world = OpsWorld()
    put(
        world.pulses,
        pulse_with(
            "worker-a",
            at(-MINUTE),
            circuit(META, CircuitState.OPEN, opened_at=at(-2 * MINUTE)),
            circuit(TELEGRAM, CircuitState.CLOSED, failures=2),
            circuit(SMTP, CircuitState.CLOSED),
        ),
        pulse_with(
            "worker-b",
            at(-MINUTE),
            circuit(META, CircuitState.HALF_OPEN, opened_at=at(-MINUTE)),
            circuit(TELEGRAM, CircuitState.CLOSED, failures=1),
            circuit(SMTP, CircuitState.CLOSED),
        ),
    )

    view = system_page(world).run(AdminSystemQuery(user_id=ADMIN))

    [worker_a] = [worker for worker in view.workers if worker.host_name == "worker-a"]
    assert [(str(item.circuit), item.state) for item in worker_a.circuits] == [
        ("provider:meta", CircuitState.OPEN),
        ("provider:telegram", CircuitState.CLOSED),
        ("provider:smtp", CircuitState.CLOSED),
    ]
    assert worker_a.circuits[0].opened_at == at(-2 * MINUTE)
    # Not closed first (open before half-open), then by name.
    assert [(str(item.circuit), item.state) for item in view.circuits] == [
        ("provider:meta", CircuitState.OPEN),
        ("provider:smtp", CircuitState.CLOSED),
        ("provider:telegram", CircuitState.CLOSED),
    ]
    meta, smtp, telegram = view.circuits
    assert meta.workers_not_closed == CircuitWorkerCount(2)
    assert meta.workers_reporting == CircuitWorkerCount(2)
    assert meta.opened_at == at(-2 * MINUTE)
    assert smtp.workers_not_closed == CircuitWorkerCount(0)
    assert smtp.opened_at is None
    assert telegram.recent_failures == CircuitFailureCount(3)


def test_a_stale_pulse_says_nothing_about_a_provider_now() -> None:
    gone = pulse_with(
        "worker-gone",
        at(-HOUR),
        circuit(META, CircuitState.OPEN, opened_at=at(-2 * HOUR)),
    )
    live = pulse_with("worker-live", at(-MINUTE), circuit(META, CircuitState.CLOSED))

    [meta] = circuit_summaries([gone, live], NOW)

    assert meta.state is CircuitState.CLOSED
    assert meta.workers_reporting == CircuitWorkerCount(1)
    assert meta.opened_at is None
    assert circuit_summaries([gone], NOW) == []


def test_failures_are_capped_and_a_page_without_circuits_is_empty() -> None:
    noisy = [
        pulse_with(
            f"worker-{number}",
            at(-MINUTE),
            circuit(TELEGRAM, CircuitState.CLOSED, failures=600),
        )
        for number in range(3)
    ]

    [telegram] = circuit_summaries(noisy, NOW)

    assert telegram.recent_failures == CircuitFailureCount(1000)
    assert circuit_summaries([pulse("worker-old", at(-MINUTE))], NOW) == []
