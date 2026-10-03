"""GET /readyz decides by the database, the migrations and the pool."""

from typed_time_provider import Microseconds, WallClock

from app.contracts.health import WorkerHeartbeatRepoContract
from app.schemas.constants.observability import (
    DatabaseProbeFailure,
    HealthCheckStatus,
    ReadinessState,
)
from app.schemas.domain.jobs import WorkerHeartbeatDocument
from app.schemas.dto.health import DatabaseProbe, ReadinessQuery, ReadinessReport
from app.schemas.exceptions.application_errors import ExternalServiceError
from app.schemas.typings.storage.constrained_integers import DocumentCount
from app.use_cases.observability.check_readiness_use_case import (
    WORKER_HEARTBEAT_STALE_SECONDS,
    CheckReadinessUseCase,
)
from app.utilities.observability.readiness_memory import ReadinessMemory
from app.utilities.storage.storage_scope_context import StorageScopeContext
from tests.platform.readiness_fakes import (
    MIGRATION_NAMES,
    SECOND,
    ScriptedProbe,
    StaticMigrationSource,
    build_heartbeat_repo,
    failed_probe,
    healthy_probe,
    heartbeat_at,
)

NOW: int = 1_790_000_000 * SECOND


class BrokenHeartbeatRepo:
    def save(self, heartbeat: WorkerHeartbeatDocument) -> None:
        del heartbeat

    def find_freshest(self) -> WorkerHeartbeatDocument | None:
        raise ExternalServiceError("The database failed (OperationalError).")

    def delete_beaten_before(self, beaten_before: Microseconds) -> DocumentCount:
        del beaten_before
        return DocumentCount(0)


def check(
    probe: DatabaseProbe,
    heartbeats: WorkerHeartbeatRepoContract | None = None,
    source: StaticMigrationSource | None = None,
    memory: ReadinessMemory | None = None,
    now: int = NOW,
) -> ReadinessReport:
    use_case = CheckReadinessUseCase(
        database_probe=ScriptedProbe(probe),
        migration_source=StaticMigrationSource() if source is None else source,
        worker_heartbeat_repo=build_heartbeat_repo()
        if heartbeats is None
        else heartbeats,
        storage_scope=StorageScopeContext(),
        wall_clock=WallClock(
            preferred_time_unit_type=Microseconds,
            unix_nanosecond_factory=lambda: now * 1000,
        ),
        memory=ReadinessMemory() if memory is None else memory,
    )
    return use_case.run(ReadinessQuery())


def test_a_healthy_database_with_every_migration_is_ready() -> None:
    heartbeats = build_heartbeat_repo()
    heartbeats.save(heartbeat_at(NOW - 7 * SECOND))

    report = check(healthy_probe(), heartbeats)

    assert report.status is ReadinessState.READY
    assert report.model_dump(mode="json", exclude_none=True)["checks"] == {
        "database": {"status": "ok", "latency_ms": 3},
        "migrations": {"status": "ok", "pending": 0},
        "pool": {"status": "ok", "in_use": 2, "size": 64},
        "worker": {
            "status": "ok",
            "heartbeat_age_seconds": 7,
            "release": "4718714",
        },
    }


def test_a_database_that_is_down_makes_the_instance_not_ready() -> None:
    report = check(failed_probe(DatabaseProbeFailure.UNREACHABLE))

    assert report.status is ReadinessState.NOT_READY
    assert report.checks.database.status is HealthCheckStatus.FAILED
    assert report.checks.database.failure is DatabaseProbeFailure.UNREACHABLE
    assert report.checks.migrations.status is HealthCheckStatus.FAILED
    assert report.checks.pool.status is HealthCheckStatus.OK


def test_a_migration_of_this_build_that_is_not_applied_is_not_ready() -> None:
    report = check(healthy_probe(applied=MIGRATION_NAMES[:1]))

    assert report.status is ReadinessState.NOT_READY
    assert report.checks.migrations.status is HealthCheckStatus.FAILED
    assert report.checks.migrations.pending == 1


def test_a_newer_database_is_fine_for_the_old_release_during_a_deploy() -> None:
    source = StaticMigrationSource(MIGRATION_NAMES[:1])

    report = check(healthy_probe(), source=source)
    check(healthy_probe(), source=source)

    assert report.status is ReadinessState.READY
    assert source.loads == 2  # one per use case instance, cached inside it


def test_unreadable_migration_files_fail_the_migrations_check() -> None:
    source = StaticMigrationSource()
    source.is_broken = True

    report = check(healthy_probe(), source=source)

    assert report.status is ReadinessState.NOT_READY
    assert report.checks.migrations.status is HealthCheckStatus.FAILED


def test_without_a_database_the_checks_are_skipped_and_the_instance_ready() -> None:
    report = check(DatabaseProbe(status=HealthCheckStatus.SKIPPED))

    assert report.status is ReadinessState.READY
    assert {
        report.checks.database.status,
        report.checks.migrations.status,
        report.checks.pool.status,
    } == {HealthCheckStatus.SKIPPED}


def test_an_old_missing_or_unreadable_worker_pulse_is_reported_not_failing() -> None:
    stale = build_heartbeat_repo()
    stale.save(heartbeat_at(NOW - (WORKER_HEARTBEAT_STALE_SECONDS + 1) * SECOND))

    old = check(healthy_probe(), stale)
    missing = check(healthy_probe())
    unreadable = check(healthy_probe(), BrokenHeartbeatRepo())

    for report in (old, missing, unreadable):
        assert report.status is ReadinessState.READY
        assert report.checks.worker.status is HealthCheckStatus.DEGRADED
    assert old.checks.worker.heartbeat_age_seconds == (
        WORKER_HEARTBEAT_STALE_SECONDS + 1
    )
    assert missing.checks.worker.heartbeat_age_seconds is None


def test_the_freshest_of_several_pulses_counts() -> None:
    heartbeats = build_heartbeat_repo()
    heartbeats.save(heartbeat_at(NOW - 3600 * SECOND))
    heartbeats.save(heartbeat_at(NOW - 2 * SECOND))
    heartbeats.save(heartbeat_at(NOW - 600 * SECOND))

    report = check(healthy_probe(), heartbeats)

    assert report.checks.worker.heartbeat_age_seconds == 2
    assert int(heartbeats.delete_beaten_before(Microseconds(NOW - 60 * SECOND))) == 2
