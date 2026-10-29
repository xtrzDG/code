"""Fakes of the readiness check: a scripted database probe and migration files."""

from typed_time_provider import Microseconds

from app.adapters.storage.in_memory_document_collection import (
    InMemoryDocumentCollectionAdapter,
)
from app.repositories.worker_heartbeat_repository import WorkerHeartbeatRepository
from app.schemas.constants.observability import DatabaseProbeFailure, HealthCheckStatus
from app.schemas.domain.jobs import WorkerHeartbeatDocument
from app.schemas.dto.health import DatabaseProbe
from app.schemas.dto.storage import SchemaMigrationScript
from app.schemas.exceptions.application_errors import ValidationFailedError
from app.schemas.typings.platform.constrained_integers import (
    DatabaseConnectionCount,
    DatabasePoolSize,
    ElapsedMilliseconds,
)
from app.schemas.typings.platform.constrained_strings import (
    ReleaseVersion,
    WorkerHostName,
)
from app.schemas.typings.storage.constrained_strings import (
    DocumentCollectionName,
    SchemaMigrationChecksum,
    SchemaMigrationName,
)
from app.schemas.typings.storage.strings import SchemaMigrationSql
from app.utilities.storage.document_lookup_fields import declared_lookup_fields

MIGRATION_NAMES: tuple[SchemaMigrationName, ...] = (
    SchemaMigrationName("0001_document_collections"),
    SchemaMigrationName("1030_worker_heartbeats"),
)
SECOND: int = 1_000_000


class ScriptedProbe:
    def __init__(self, probe: DatabaseProbe) -> None:
        self.result: DatabaseProbe = probe
        self.calls: int = 0

    def probe(self) -> DatabaseProbe:
        self.calls += 1
        return self.result


class StaticMigrationSource:
    def __init__(
        self, names: tuple[SchemaMigrationName, ...] = MIGRATION_NAMES
    ) -> None:
        self.names: tuple[SchemaMigrationName, ...] = names
        self.loads: int = 0
        self.is_broken: bool = False

    def load_scripts(self) -> list[SchemaMigrationScript]:
        self.loads += 1
        if self.is_broken:
            raise ValidationFailedError("Migrations directory 'x' does not exist.")

        return [
            SchemaMigrationScript(
                name=name,
                checksum=SchemaMigrationChecksum("0" * 64),
                sql=SchemaMigrationSql("select 1"),
            )
            for name in self.names
        ]


def healthy_probe(
    applied: tuple[SchemaMigrationName, ...] = MIGRATION_NAMES,
) -> DatabaseProbe:
    return DatabaseProbe(
        status=HealthCheckStatus.OK,
        latency=ElapsedMilliseconds(3),
        applied_migrations=list(applied),
        connections_in_use=DatabaseConnectionCount(2),
        pool_size=DatabasePoolSize(64),
    )


def failed_probe(failure: DatabaseProbeFailure) -> DatabaseProbe:
    return DatabaseProbe(
        status=HealthCheckStatus.FAILED,
        failure=failure,
        connections_in_use=DatabaseConnectionCount(64),
        pool_size=DatabasePoolSize(64),
    )


def build_heartbeat_repo() -> WorkerHeartbeatRepository:
    return WorkerHeartbeatRepository(
        InMemoryDocumentCollectionAdapter[WorkerHeartbeatDocument](
            WorkerHeartbeatDocument,
            declared_lookup_fields(
                DocumentCollectionName("worker_heartbeats"), WorkerHeartbeatDocument
            ),
        )
    )


def heartbeat_at(
    beat_at: int, started_at: int | None = None
) -> WorkerHeartbeatDocument:
    start: int = beat_at if started_at is None else started_at
    return WorkerHeartbeatDocument(
        host_name=WorkerHostName("worker-1"),
        release=ReleaseVersion("4718714"),
        started_at=Microseconds(start),
        beat_at=Microseconds(beat_at),
        created_at=Microseconds(start),
        updated_at=Microseconds(beat_at),
    )
