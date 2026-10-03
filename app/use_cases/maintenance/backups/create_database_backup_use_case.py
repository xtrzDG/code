from typed_time_provider import Microseconds, WallClock

from app.contracts.backups import (
    BackupBucketClientContract,
    BackupCipherAdapterContract,
    DatabaseDumpAdapterContract,
)
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.dto.backups import (
    BackupArchive,
    BackupManifest,
    CreateDatabaseBackupCommand,
    DatabaseBackupReport,
    DatabaseFacts,
)
from app.schemas.exceptions.backup_errors import BackupToolError
from app.schemas.typings.backups.constrained_integers import BackupCopyCount
from app.schemas.typings.backups.constrained_strings import (
    BackupObjectKey,
    BackupObjectPrefix,
)
from app.schemas.typings.platform.strings import LocalFilePath
from app.utilities.backups.archive_files import (
    file_digest,
    remove_file,
    work_file,
    write_manifest,
)
from app.utilities.backups.backup_keys import (
    archive_key,
    manifest_key,
    recognize_archives,
)
from app.utilities.backups.backup_retention import select_kept_archives


class CreateDatabaseBackupUseCase(
    UseCaseContract[CreateDatabaseBackupCommand, DatabaseBackupReport]
):
    """
    The off-site backup (`workshop backup`, a daily Render cron job).

    The database is dumped in one consistent snapshot (a database without
    the application schema is refused: the wrong DATABASE_URL), encrypted
    with age
    to the configured public keys (the plaintext dump is deleted at once)
    and uploaded to the EU backup bucket, then its manifest (the snapshot's
    row counts, migrations and row-level security, the archive's size and
    SHA-256). The manifest goes up last, so an archive with a manifest is
    complete. Retention then keeps the newest backup of each of the last
    days and months and deletes the other archives with their manifests.
    """

    def __init__(
        self,
        database_dump: DatabaseDumpAdapterContract,
        backup_cipher: BackupCipherAdapterContract,
        backup_bucket: BackupBucketClientContract,
        wall_clock: WallClock[Microseconds],
        prefix: BackupObjectPrefix,
        daily_copies: BackupCopyCount,
        monthly_copies: BackupCopyCount,
    ) -> None:
        self._database_dump: DatabaseDumpAdapterContract = database_dump
        self._backup_cipher: BackupCipherAdapterContract = backup_cipher
        self._backup_bucket: BackupBucketClientContract = backup_bucket
        self._wall_clock: WallClock[Microseconds] = wall_clock
        self._prefix: BackupObjectPrefix = prefix
        self._daily_copies: BackupCopyCount = daily_copies
        self._monthly_copies: BackupCopyCount = monthly_copies

    def run(self, input_data: CreateDatabaseBackupCommand) -> DatabaseBackupReport:
        started_at: Microseconds = self._wall_clock.now_unix()
        key: BackupObjectKey = archive_key(self._prefix, started_at)
        dump_file: LocalFilePath = work_file(input_data.work_directory, "dump.pgc")
        archive_file: LocalFilePath = work_file(input_data.work_directory, "dump.age")
        manifest_file: LocalFilePath = work_file(
            input_data.work_directory, "manifest.json"
        )
        try:
            facts: DatabaseFacts = self._database_dump.dump(dump_file)
            if not facts.applied_migrations:
                # Retention would soon replace every good backup with this.
                raise BackupToolError(
                    "The database has no application schema (no applied "
                    "migrations): DATABASE_URL names the wrong database. "
                    "Nothing was uploaded."
                )
            self._backup_cipher.encrypt_file(dump_file, archive_file)
        finally:
            remove_file(dump_file)

        checksum, size = file_digest(archive_file)
        self._backup_bucket.upload_file(key, archive_file)
        remove_file(archive_file)
        manifest = BackupManifest(
            archive_key=key,
            created_at=started_at,
            archive_size=size,
            archive_checksum=checksum,
            facts=facts,
        )
        write_manifest(manifest, manifest_file)
        self._backup_bucket.upload_file(manifest_key(key), manifest_file)
        kept, deleted = self._apply_retention(key, started_at)
        return DatabaseBackupReport(
            manifest=manifest, kept_keys=kept, deleted_keys=deleted
        )

    def _apply_retention(
        self,
        new_key: BackupObjectKey,
        started_at: Microseconds,
    ) -> tuple[list[BackupObjectKey], list[BackupObjectKey]]:
        archives: list[BackupArchive] = recognize_archives(
            self._backup_bucket.list_objects(self._prefix), self._prefix
        )
        if new_key not in {archive.key for archive in archives}:
            # A listing may lag behind the upload it follows.
            archives.append(
                BackupArchive(
                    key=new_key,
                    manifest_key=manifest_key(new_key),
                    created_at=started_at,
                )
            )

        kept_keys: set[BackupObjectKey] = select_kept_archives(
            archives, self._daily_copies, self._monthly_copies
        )
        deleted: list[BackupObjectKey] = []
        for archive in archives:
            if archive.key in kept_keys:
                continue

            self._backup_bucket.delete_object(archive.manifest_key)
            self._backup_bucket.delete_object(archive.key)
            deleted.append(archive.key)

        kept: list[BackupObjectKey] = [
            archive.key for archive in archives if archive.key in kept_keys
        ]
        return kept, deleted
