"""
A busy connection pool is load, not a broken instance: GET /readyz keeps
the instance in rotation unless the pool stays exhausted for more than
30 s, and fails only on an unreachable database or missing migrations.
"""

from app.schemas.constants.observability import (
    DatabaseProbeFailure,
    HealthCheckStatus,
    ReadinessState,
)
from app.use_cases.observability.check_readiness_use_case import (
    POOL_EXHAUSTION_LIMIT_SECONDS,
)
from app.utilities.observability.readiness_memory import ReadinessMemory
from tests.platform.readiness_fakes import (
    MIGRATION_NAMES,
    SECOND,
    failed_probe,
    healthy_probe,
)
from tests.platform.test_readiness_check import NOW, check

EXHAUSTED = failed_probe(DatabaseProbeFailure.POOL_EXHAUSTED)


def test_an_exhausted_pool_degrades_but_keeps_the_instance_in_rotation() -> None:
    memory = ReadinessMemory()
    check(healthy_probe(), memory=memory, now=NOW - 60 * SECOND)

    report = check(EXHAUSTED, memory=memory)

    assert report.status is ReadinessState.READY
    assert report.checks.pool.status is HealthCheckStatus.DEGRADED
    assert report.checks.pool.in_use == 64
    assert report.checks.pool.exhausted_seconds == 0
    # The database answered a moment ago; the migrations keep their reading.
    assert report.checks.database.status is HealthCheckStatus.DEGRADED
    assert report.checks.database.failure is DatabaseProbeFailure.POOL_EXHAUSTED
    assert report.checks.migrations.status is HealthCheckStatus.OK


def test_a_pool_exhausted_for_longer_than_the_limit_fails() -> None:
    memory = ReadinessMemory()
    started = NOW - (POOL_EXHAUSTION_LIMIT_SECONDS + 1) * SECOND
    check(EXHAUSTED, memory=memory, now=started)

    within = check(EXHAUSTED, memory=memory, now=started + 30 * SECOND)
    beyond = check(EXHAUSTED, memory=memory)

    assert within.status is ReadinessState.READY
    assert within.checks.pool.exhausted_seconds == 30
    assert beyond.status is ReadinessState.NOT_READY
    assert beyond.checks.pool.status is HealthCheckStatus.FAILED
    assert beyond.checks.pool.exhausted_seconds == POOL_EXHAUSTION_LIMIT_SECONDS + 1


def test_a_free_connection_between_probes_starts_the_window_again() -> None:
    memory = ReadinessMemory()
    check(EXHAUSTED, memory=memory, now=NOW - 40 * SECOND)
    check(healthy_probe(), memory=memory, now=NOW - 20 * SECOND)

    report = check(EXHAUSTED, memory=memory)

    assert report.status is ReadinessState.READY
    assert report.checks.pool.exhausted_seconds == 0


def test_migrations_unknown_or_known_missing_while_the_pool_is_busy() -> None:
    unknown = check(EXHAUSTED, memory=ReadinessMemory())
    missing_memory = ReadinessMemory()
    check(healthy_probe(applied=MIGRATION_NAMES[:1]), memory=missing_memory)
    missing = check(EXHAUSTED, memory=missing_memory)

    assert unknown.status is ReadinessState.READY
    assert unknown.checks.migrations.status is HealthCheckStatus.DEGRADED
    assert missing.status is ReadinessState.NOT_READY
    assert missing.checks.migrations.status is HealthCheckStatus.FAILED


def test_an_unreachable_database_still_fails_at_once() -> None:
    memory = ReadinessMemory()
    check(healthy_probe(), memory=memory)

    report = check(failed_probe(DatabaseProbeFailure.UNREACHABLE), memory=memory)

    assert report.status is ReadinessState.NOT_READY
    assert report.checks.database.status is HealthCheckStatus.FAILED
