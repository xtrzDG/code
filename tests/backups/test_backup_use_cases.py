"""The backup and the restore drill over fakes of the bucket and databases."""

import hashlib
from pathlib import Path

import pytest

from app.adapters.backup.age_backup_cipher_adapter import AgeBackupCipherAdapter
from app.adapters.storage.postgres.sql_file_migration_source_adapter import (
    SqlFileMigrationSourceAdapter,
)
from app.schemas.dto.backups import (
    BackupManifest,
    CheckBackupRestoreCommand,
    CreateDatabaseBackupCommand,
    DatabaseBackupReport,
    DatabaseFacts,
)
from app.schemas.exceptions.application_errors import (
    NotFoundError,
    ValidationFailedError,
)
from app.schemas.exceptions.backup_errors import (
    BackupArchiveCorruptError,
    BackupToolError,
)
from app.schemas.typings.backups.constrained_integers import (
    BackupCopyCount,
    BackupFreshnessHours,
)
from app.schemas.typings.backups.constrained_strings import (
    AgeIdentity,
    BackupChecksum,
    BackupObjectKey,
)
from app.schemas.typings.platform.strings import LocalDirectoryPath, LocalFilePath
from app.use_cases.maintenance.backups.check_backup_restore_use_case import (
    CheckBackupRestoreUseCase,
)
from app.use_cases.maintenance.backups.create_database_backup_use_case import (
    CreateDatabaseBackupUseCase,
)
from app.utilities.security.age.age_keys import recipient_of
from app.utilities.storage.schema_migration_files import compute_migration_checksum
from tests.backups.age_test_keys import generate_identity
from tests.backups.backup_fakes import (
    DUMP_BYTES,
    PREFIX,
    FakeDatabaseDump,
    FakeScratchDatabase,
    InMemoryBackupBucket,
    build_facts,
    clock_at,
)

IDENTITY: AgeIdentity = generate_identity()
MIGRATION_SQL: str = "select 1;\n"


def facts(bookings: int = 3) -> DatabaseFacts:
    """Facts whose migration is the work directory's file."""

    return build_facts(bookings, checksum=compute_migration_checksum(MIGRATION_SQL))


def take_backup(
    bucket: InMemoryBackupBucket,
    work: Path,
    at: str,
    dumped: DatabaseFacts | None = None,
) -> DatabaseBackupReport:
    return CreateDatabaseBackupUseCase(
        database_dump=FakeDatabaseDump(facts() if dumped is None else dumped),
        backup_cipher=AgeBackupCipherAdapter([recipient_of(IDENTITY)]),
        backup_bucket=bucket,
        wall_clock=clock_at(at),
        prefix=PREFIX,
        daily_copies=BackupCopyCount(2),
        monthly_copies=BackupCopyCount(1),
    ).run(CreateDatabaseBackupCommand(work_directory=LocalDirectoryPath(str(work))))


def drill(
    bucket: InMemoryBackupBucket,
    work: Path,
    scratch: FakeScratchDatabase,
    at: str = "2026-10-03T02:00:00",
) -> CheckBackupRestoreUseCase:
    return CheckBackupRestoreUseCase(
        backup_bucket=bucket,
        backup_cipher=AgeBackupCipherAdapter([], IDENTITY),
        scratch_database=scratch,
        migration_source=SqlFileMigrationSourceAdapter(work / "migrations"),
        wall_clock=clock_at(at),
        prefix=PREFIX,
        max_age=BackupFreshnessHours(26),
    )


def command(work: Path, archive: str | None = None) -> CheckBackupRestoreCommand:
    return CheckBackupRestoreCommand(
        work_directory=LocalDirectoryPath(str(work)),
        archive_key=None if archive is None else BackupObjectKey(archive),
    )


@pytest.fixture
def work(tmp_path: Path) -> Path:
    migrations = tmp_path / "migrations"
    migrations.mkdir()
    (migrations / "0001_document_collections.sql").write_text(MIGRATION_SQL)
    return tmp_path


def test_a_backup_uploads_an_encrypted_archive_and_its_manifest(work: Path) -> None:
    bucket = InMemoryBackupBucket()

    report = take_backup(bucket, work, "2026-10-03T01:07:00")

    key = "workshop/2026/10/20261003T010700Z.pgdump.age"
    assert sorted(bucket.objects) == [key.replace(".pgdump.age", ".manifest.json"), key]
    assert bucket.objects[key].startswith(b"age-encryption.org/v1\n")
    assert DUMP_BYTES not in bucket.objects[key]
    manifest = BackupManifest.model_validate_json(
        bucket.objects[key.replace(".pgdump.age", ".manifest.json")]
    )
    assert manifest == report.manifest
    assert int(manifest.archive_size) == len(bucket.objects[key])
    assert manifest.facts == facts()
    assert sorted(path.name for path in work.iterdir()) == [
        "manifest.json",
        "migrations",
    ]


def test_a_database_without_migrations_is_not_backed_up(work: Path) -> None:
    bucket = InMemoryBackupBucket()

    with pytest.raises(BackupToolError, match="no application schema"):
        take_backup(bucket, work, "2026-10-03T01:07:00", build_facts(migrations=()))

    assert bucket.objects == {}
    assert sorted(path.name for path in work.iterdir()) == ["migrations"]


def test_a_refused_upload_leaves_no_files_behind(work: Path) -> None:
    bucket = InMemoryBackupBucket()
    bucket.refused_uploads = 1

    with pytest.raises(BackupToolError, match="refused an upload"):
        take_backup(bucket, work, "2026-10-03T01:07:00")

    assert bucket.objects == {}
    assert sorted(path.name for path in work.iterdir()) == ["migrations"]


def test_retention_deletes_old_archives_with_their_manifests(work: Path) -> None:
    bucket = InMemoryBackupBucket()
    bucket.objects["workshop/README.txt"] = b"not an archive"
    for day in ("2026-08-30", "2026-09-29", "2026-09-30", "2026-10-01", "2026-10-02"):
        take_backup(bucket, work, f"{day}T01:07:00")

    report = take_backup(bucket, work, "2026-10-03T01:07:00")

    assert [str(key) for key in report.kept_keys] == [
        "workshop/2026/10/20261002T010700Z.pgdump.age",
        "workshop/2026/10/20261003T010700Z.pgdump.age",
    ]
    assert sorted(bucket.objects) == [
        "workshop/2026/10/20261002T010700Z.manifest.json",
        "workshop/2026/10/20261002T010700Z.pgdump.age",
        "workshop/2026/10/20261003T010700Z.manifest.json",
        "workshop/2026/10/20261003T010700Z.pgdump.age",
        "workshop/README.txt",
    ]


def test_the_drill_restores_the_newest_backup_and_passes(work: Path) -> None:
    bucket = InMemoryBackupBucket()
    take_backup(bucket, work, "2026-10-02T01:07:00")
    take_backup(bucket, work, "2026-10-03T01:07:00")
    scratch = FakeScratchDatabase(facts())

    report = drill(bucket, work, scratch).run(command(work))

    assert str(report.archive_key).endswith("20261003T010700Z.pgdump.age")
    assert scratch.restored_dumps == [DUMP_BYTES]
    assert report.problems == []
    assert report.pending_migrations == []
    assert sorted(path.name for path in work.iterdir()) == [
        "manifest.json",
        "migrations",
    ]


def test_the_drill_restores_a_named_archive_and_reports_differences(
    work: Path,
) -> None:
    bucket = InMemoryBackupBucket()
    take_backup(bucket, work, "2026-10-02T01:07:00")
    take_backup(bucket, work, "2026-10-03T01:07:00")
    scratch = FakeScratchDatabase(facts(bookings=2))
    older = "workshop/2026/10/20261002T010700Z.pgdump.age"

    report = drill(bucket, work, scratch, at="2026-10-05T01:07:00").run(
        command(work, older)
    )

    assert str(report.archive_key) == older
    assert [str(problem) for problem in report.problems] == [
        "The newest backup is 48 hours old (at most 26 allowed): the backup job "
        "has not run on time.",
        "workshop.bookings: 2 rows restored, 3 dumped.",
    ]
    with pytest.raises(NotFoundError, match="no backup workshop/nope"):
        drill(bucket, work, scratch).run(command(work, "workshop/nope"))


def test_an_empty_bucket_has_nothing_to_restore(work: Path) -> None:
    with pytest.raises(NotFoundError, match="no backup under workshop/"):
        drill(InMemoryBackupBucket(), work, FakeScratchDatabase(facts())).run(
            command(work)
        )


def test_a_changed_archive_is_refused_before_restoring(work: Path) -> None:
    bucket = InMemoryBackupBucket()
    take_backup(bucket, work, "2026-10-03T01:07:00")
    key = "workshop/2026/10/20261003T010700Z.pgdump.age"
    original: bytes = bucket.objects[key]
    bucket.objects[key] = original[:-1] + b"!"
    scratch = FakeScratchDatabase(facts())

    with pytest.raises(BackupArchiveCorruptError, match="SHA-256 .* differs"):
        drill(bucket, work, scratch).run(command(work))

    bucket.objects[key] = original[:-10]
    with pytest.raises(BackupArchiveCorruptError, match="cut off or changed"):
        drill(bucket, work, scratch).run(command(work))

    # Archive and manifest both rewritten: the archive itself does not open.
    manifest_key = key.replace(".pgdump.age", ".manifest.json")
    manifest = BackupManifest.model_validate_json(bucket.objects[manifest_key])
    bucket.objects[key] = original[:-1] + b"!"
    digest = hashlib.sha256(bucket.objects[key]).hexdigest()
    bucket.objects[manifest_key] = (
        manifest.model_copy(update={"archive_checksum": BackupChecksum(digest)})
        .model_dump_json()
        .encode()
    )
    with pytest.raises(BackupArchiveCorruptError, match="does not open"):
        drill(bucket, work, scratch).run(command(work))
    assert scratch.restored_dumps == []
    assert sorted(path.name for path in work.iterdir()) == [
        "manifest.json",
        "migrations",
    ]


def test_a_missing_or_foreign_manifest_fails_the_drill(work: Path) -> None:
    bucket = InMemoryBackupBucket()
    take_backup(bucket, work, "2026-10-02T01:07:00")
    take_backup(bucket, work, "2026-10-03T01:07:00")
    newest = "workshop/2026/10/20261003T010700Z.manifest.json"
    older = "workshop/2026/10/20261002T010700Z.manifest.json"
    scratch = FakeScratchDatabase(facts())

    bucket.objects[newest] = bucket.objects[older]
    with pytest.raises(BackupArchiveCorruptError, match="describes another archive"):
        drill(bucket, work, scratch).run(command(work))

    bucket.objects[newest] = b"{}"
    with pytest.raises(BackupArchiveCorruptError, match="not a backup manifest"):
        drill(bucket, work, scratch).run(command(work))

    del bucket.objects[newest]
    with pytest.raises(BackupArchiveCorruptError, match="did not finish"):
        drill(bucket, work, scratch).run(command(work))


def test_an_archive_without_an_identity_cannot_be_opened(work: Path) -> None:
    with pytest.raises(ValidationFailedError, match="BACKUP_AGE_PUBLIC_KEY"):
        AgeBackupCipherAdapter([]).encrypt_file(
            LocalFilePath(str(work / "a")), LocalFilePath(str(work / "b"))
        )
    with pytest.raises(ValidationFailedError, match="BACKUP_AGE_IDENTITY"):
        AgeBackupCipherAdapter([recipient_of(IDENTITY)]).decrypt_file(
            LocalFilePath(str(work / "a")), LocalFilePath(str(work / "b"))
        )
