"""Off-site database backups and the restore drill that proves them."""

from base_pydantic_schemas import ImmutableDTO
from pydantic import Field
from typed_time_provider import Microseconds

from app.schemas.typings.backups.booleans import IsScratchDatabaseKept
from app.schemas.typings.backups.constrained_integers import (
    BackupArchiveSize,
    DatabasePolicyCount,
    TableRowCount,
)
from app.schemas.typings.backups.constrained_strings import (
    BackupChecksum,
    BackupObjectKey,
    DatabaseTableName,
    ScratchDatabaseName,
)
from app.schemas.typings.backups.strings import RestoreCheckProblem
from app.schemas.typings.platform.strings import LocalDirectoryPath
from app.schemas.typings.storage.constrained_strings import (
    SchemaMigrationChecksum,
    SchemaMigrationName,
)


class BackupObjectListing(ImmutableDTO):
    """One object listed in the backup bucket."""

    key: BackupObjectKey
    size: BackupArchiveSize


class BackupArchive(ImmutableDTO):
    """An encrypted dump in the bucket, recognized by its key's time."""

    key: BackupObjectKey
    manifest_key: BackupObjectKey
    created_at: Microseconds


class RecordedMigration(ImmutableDTO):
    """A migration the dumped database had applied (schema_migrations)."""

    name: SchemaMigrationName
    checksum: SchemaMigrationChecksum


class DatabaseFacts(ImmutableDTO):
    """
    What a database holds, counted in one snapshot: the rows of every table
    of the application schema, the applied migrations, the tables with
    forced row-level security and the number of policies. The backup
    records them as the dump is taken; the drill counts the restored
    database again and compares.
    """

    row_counts: dict[DatabaseTableName, TableRowCount] = Field(
        default_factory=dict[DatabaseTableName, TableRowCount]
    )
    applied_migrations: list[RecordedMigration] = Field(
        default_factory=list[RecordedMigration]
    )
    secured_tables: list[DatabaseTableName] = Field(
        default_factory=list[DatabaseTableName]
    )
    policy_count: DatabasePolicyCount = DatabasePolicyCount(0)


class BackupManifest(ImmutableDTO):
    """
    The plain-text companion of an archive (`<time>.manifest.json`): when
    it was taken, the archive's size and SHA-256, and the facts of the
    dumped snapshot. Table names and counts only, never row contents.
    """

    archive_key: BackupObjectKey
    created_at: Microseconds
    archive_size: BackupArchiveSize
    archive_checksum: BackupChecksum
    facts: DatabaseFacts


class IsolationProbe(ImmutableDTO):
    """
    Row-level security of one table of the restored database, seen by a
    role that is neither superuser nor BYPASSRLS: rows visible without a
    scope (must be none), rows of the probed business visible in its scope
    and rows of other businesses visible there (must be none).
    """

    table: DatabaseTableName
    unscoped_rows: TableRowCount
    own_rows: TableRowCount
    expected_own_rows: TableRowCount
    foreign_rows: TableRowCount


class RestoredDatabase(ImmutableDTO):
    """What the drill found in the restored scratch database."""

    scratch_database: ScratchDatabaseName
    facts: DatabaseFacts
    isolation_probes: list[IsolationProbe] = Field(default_factory=list[IsolationProbe])


class CreateDatabaseBackupCommand(ImmutableDTO):
    """Dump, encrypt and upload the database; work files go to the directory."""

    work_directory: LocalDirectoryPath


class DatabaseBackupReport(ImmutableDTO):
    """What one backup run uploaded and which older archives it removed."""

    manifest: BackupManifest
    kept_keys: list[BackupObjectKey] = Field(default_factory=list[BackupObjectKey])
    deleted_keys: list[BackupObjectKey] = Field(default_factory=list[BackupObjectKey])


class CheckBackupRestoreCommand(ImmutableDTO):
    """
    Restore an archive (the newest unless one is named) into a scratch
    database and check it; the scratch database is dropped afterwards
    unless it is kept for a real restore.
    """

    work_directory: LocalDirectoryPath
    archive_key: BackupObjectKey | None = None
    is_scratch_database_kept: IsScratchDatabaseKept = False


class RestoreCheckReport(ImmutableDTO):
    """
    The drill's verdict: the archive it restored, what it found, this
    checkout's migrations newer than the backup (a restore applies them)
    and every check that failed (none: the backup is proven restorable).
    """

    archive_key: BackupObjectKey
    archive_created_at: Microseconds
    manifest: BackupManifest
    restored: RestoredDatabase
    pending_migrations: list[SchemaMigrationName] = Field(
        default_factory=list[SchemaMigrationName]
    )
    problems: list[RestoreCheckProblem] = Field(
        default_factory=list[RestoreCheckProblem]
    )
