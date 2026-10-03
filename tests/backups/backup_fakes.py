"""Fakes of the backup contracts and builders of facts for the tests."""

from datetime import UTC, datetime
from pathlib import Path

from typed_time_provider import Microseconds, WallClock

from app.contracts.backups import (
    BackupBucketClientContract,
    DatabaseDumpAdapterContract,
    ScratchDatabaseAdapterContract,
)
from app.schemas.dto.backups import (
    BackupObjectListing,
    DatabaseFacts,
    IsolationProbe,
    RecordedMigration,
    RestoredDatabase,
)
from app.schemas.exceptions.backup_errors import BackupToolError
from app.schemas.typings.backups.booleans import IsScratchDatabaseKept
from app.schemas.typings.backups.constrained_integers import (
    BackupArchiveSize,
    DatabasePolicyCount,
    TableRowCount,
)
from app.schemas.typings.backups.constrained_strings import (
    BackupObjectKey,
    BackupObjectPrefix,
    DatabaseTableName,
    ScratchDatabaseName,
)
from app.schemas.typings.platform.strings import LocalFilePath
from app.schemas.typings.storage.constrained_strings import (
    SchemaMigrationChecksum,
    SchemaMigrationName,
)

PREFIX: BackupObjectPrefix = BackupObjectPrefix("workshop/")
CHECKSUM: SchemaMigrationChecksum = SchemaMigrationChecksum("a" * 64)
DUMP_BYTES: bytes = b"PGDMP custom-format dump of the platform"


def moment(text: str) -> Microseconds:
    """Microseconds of an ISO time in UTC ("2026-10-03T01:07:00")."""

    parsed = datetime.fromisoformat(text).replace(tzinfo=UTC)
    return Microseconds(int(parsed.timestamp()) * 1_000_000)


def clock_at(text: str) -> WallClock[Microseconds]:
    nanoseconds: int = int(moment(text)) * 1_000
    return WallClock(
        preferred_time_unit_type=Microseconds,
        unix_nanosecond_factory=lambda: nanoseconds,
    )


def build_facts(
    bookings: int = 3,
    migrations: tuple[str, ...] = ("0001_document_collections",),
    checksum: SchemaMigrationChecksum = CHECKSUM,
) -> DatabaseFacts:
    return DatabaseFacts(
        row_counts={
            DatabaseTableName("workshop.bookings"): TableRowCount(bookings),
            DatabaseTableName("workshop.businesses"): TableRowCount(2),
            DatabaseTableName("workshop.schema_migrations"): TableRowCount(
                len(migrations)
            ),
        },
        applied_migrations=[
            RecordedMigration(name=SchemaMigrationName(name), checksum=checksum)
            for name in migrations
        ],
        secured_tables=[
            DatabaseTableName("workshop.bookings"),
            DatabaseTableName("workshop.businesses"),
        ],
        policy_count=DatabasePolicyCount(2),
    )


def clean_probes(facts: DatabaseFacts) -> list[IsolationProbe]:
    return [
        IsolationProbe(
            table=table,
            unscoped_rows=TableRowCount(0),
            own_rows=TableRowCount(1),
            expected_own_rows=TableRowCount(1),
            foreign_rows=TableRowCount(0),
        )
        for table in facts.secured_tables
    ]


class InMemoryBackupBucket(BackupBucketClientContract):
    def __init__(self) -> None:
        self.objects: dict[str, bytes] = {}
        self.deleted: list[str] = []
        self.refused_uploads: int = 0

    def upload_file(self, key: BackupObjectKey, source: LocalFilePath) -> None:
        if self.refused_uploads:
            self.refused_uploads -= 1
            raise BackupToolError(f"The backup bucket refused an upload of {key}.")

        self.objects[str(key)] = Path(str(source)).read_bytes()

    def download_file(self, key: BackupObjectKey, target: LocalFilePath) -> bool:
        content: bytes | None = self.objects.get(str(key))
        if content is None:
            return False

        Path(str(target)).write_bytes(content)
        return True

    def list_objects(self, prefix: BackupObjectPrefix) -> list[BackupObjectListing]:
        return [
            BackupObjectListing(
                key=BackupObjectKey(key), size=BackupArchiveSize(len(content))
            )
            for key, content in sorted(self.objects.items())
            if key.startswith(str(prefix))
        ]

    def delete_object(self, key: BackupObjectKey) -> None:
        self.deleted.append(str(key))
        self.objects.pop(str(key), None)


class FakeDatabaseDump(DatabaseDumpAdapterContract):
    def __init__(self, facts: DatabaseFacts) -> None:
        self.facts: DatabaseFacts = facts

    def dump(self, target: LocalFilePath) -> DatabaseFacts:
        Path(str(target)).write_bytes(DUMP_BYTES)
        return self.facts


class FakeScratchDatabase(ScratchDatabaseAdapterContract):
    """Restores by reading the dump; reports the facts it was given."""

    def __init__(self, facts: DatabaseFacts) -> None:
        self.facts: DatabaseFacts = facts
        self.restored_dumps: list[bytes] = []
        self.kept: list[bool] = []

    def restore_and_inspect(
        self,
        archive: LocalFilePath,
        is_kept: IsScratchDatabaseKept,
    ) -> RestoredDatabase:
        self.restored_dumps.append(Path(str(archive)).read_bytes())
        self.kept.append(is_kept)
        return RestoredDatabase(
            scratch_database=ScratchDatabaseName("restore_drill_test"),
            facts=self.facts,
            isolation_probes=clean_probes(self.facts),
        )
