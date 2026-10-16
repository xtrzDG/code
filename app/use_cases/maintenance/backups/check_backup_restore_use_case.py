from typed_time_provider import Microseconds, WallClock

from app.contracts.backups import (
    BackupBucketClientContract,
    BackupCipherAdapterContract,
    ScratchDatabaseAdapterContract,
)
from app.contracts.storage import SchemaMigrationSourceAdapterContract
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.dto.backups import (
    BackupArchive,
    BackupManifest,
    CheckBackupRestoreCommand,
    RestoreCheckReport,
    RestoredDatabase,
)
from app.schemas.dto.storage import SchemaMigrationScript
from app.schemas.exceptions.application_errors import NotFoundError
from app.schemas.exceptions.backup_errors import BackupArchiveCorruptError
from app.schemas.typings.backups.constrained_integers import BackupFreshnessHours
from app.schemas.typings.backups.constrained_strings import BackupObjectPrefix
from app.schemas.typings.platform.strings import LocalFilePath
from app.utilities.backups.archive_files import (
    file_digest,
    read_manifest,
    remove_file,
    work_file,
)
from app.utilities.backups.backup_keys import recognize_archives
from app.utilities.backups.restore_verdict import (
    check_freshness,
    judge_restore,
    pending_migrations,
)


class CheckBackupRestoreUseCase(
    UseCaseContract[CheckBackupRestoreCommand, RestoreCheckReport]
):
    """
    The restore drill (`workshop restore-check`, weekly and in CI): proves
    that the newest off-site backup restores into a working database.

    The archive is downloaded, checked against its manifest (size, SHA-256),
    decrypted with the drill's identity and restored into a throwaway
    database. The drill then compares every table's row count with the
    manifest, the applied migrations with this checkout's files, and probes
    row-level security as a bound role; the newest backup must also be
    recent. Every failed check is reported (the CLI then exits non-zero and
    Sentry Crons records the failure); a damaged archive raises
    BackupArchiveCorruptError at once.
    """

    def __init__(
        self,
        backup_bucket: BackupBucketClientContract,
        backup_cipher: BackupCipherAdapterContract,
        scratch_database: ScratchDatabaseAdapterContract,
        migration_source: SchemaMigrationSourceAdapterContract,
        wall_clock: WallClock[Microseconds],
        prefix: BackupObjectPrefix,
        max_age: BackupFreshnessHours,
    ) -> None:
        self._backup_bucket: BackupBucketClientContract = backup_bucket
        self._backup_cipher: BackupCipherAdapterContract = backup_cipher
        self._scratch_database: ScratchDatabaseAdapterContract = scratch_database
        self._migration_source: SchemaMigrationSourceAdapterContract = migration_source
        self._wall_clock: WallClock[Microseconds] = wall_clock
        self._prefix: BackupObjectPrefix = prefix
        self._max_age: BackupFreshnessHours = max_age

    def run(self, input_data: CheckBackupRestoreCommand) -> RestoreCheckReport:
        archives: list[BackupArchive] = recognize_archives(
            self._backup_bucket.list_objects(self._prefix), self._prefix
        )
        archive: BackupArchive = choose_archive(archives, input_data, self._prefix)
        manifest: BackupManifest = self._fetch_manifest(archive, input_data)
        dump_file: LocalFilePath = self._fetch_dump(archive, manifest, input_data)
        try:
            restored: RestoredDatabase = self._scratch_database.restore_and_inspect(
                dump_file, input_data.is_scratch_database_kept
            )
        finally:
            remove_file(dump_file)

        repository: list[SchemaMigrationScript] = self._migration_source.load_scripts()
        newest: BackupArchive = archives[-1]
        return RestoreCheckReport(
            archive_key=archive.key,
            archive_created_at=archive.created_at,
            manifest=manifest,
            restored=restored,
            pending_migrations=pending_migrations(
                restored.facts.applied_migrations, repository
            ),
            problems=[
                *check_freshness(
                    newest.created_at, self._wall_clock.now_unix(), self._max_age
                ),
                *judge_restore(manifest, restored, repository),
            ],
        )

    def _fetch_manifest(
        self,
        archive: BackupArchive,
        input_data: CheckBackupRestoreCommand,
    ) -> BackupManifest:
        manifest_file = work_file(input_data.work_directory, "manifest.json")
        if not self._backup_bucket.download_file(archive.manifest_key, manifest_file):
            raise BackupArchiveCorruptError(
                f"The manifest of {archive.key} is missing: the backup did not finish."
            )

        try:
            manifest: BackupManifest = read_manifest(manifest_file)
        except ValueError as error:
            raise BackupArchiveCorruptError(
                f"The manifest of {archive.key} is not a backup manifest."
            ) from error

        if manifest.archive_key != archive.key:
            raise BackupArchiveCorruptError(
                f"The manifest of {archive.key} describes another archive."
            )

        return manifest

    def _fetch_dump(
        self,
        archive: BackupArchive,
        manifest: BackupManifest,
        input_data: CheckBackupRestoreCommand,
    ) -> LocalFilePath:
        archive_file = work_file(input_data.work_directory, "dump.age")
        dump_file = work_file(input_data.work_directory, "dump.pgc")
        if not self._backup_bucket.download_file(archive.key, archive_file):
            raise NotFoundError(f"The archive {archive.key} disappeared.")

        try:
            checksum, size = file_digest(archive_file)
            if size != manifest.archive_size:
                raise BackupArchiveCorruptError(
                    f"{archive.key} has {int(size)} bytes, its manifest "
                    f"{int(manifest.archive_size)}: it was cut off or changed."
                )
            if checksum != manifest.archive_checksum:
                raise BackupArchiveCorruptError(
                    f"The SHA-256 of {archive.key} differs from its manifest: it "
                    "was changed."
                )

            self._backup_cipher.decrypt_file(archive_file, dump_file)
        finally:
            remove_file(archive_file)

        return dump_file


def choose_archive(
    archives: list[BackupArchive],
    input_data: CheckBackupRestoreCommand,
    prefix: BackupObjectPrefix,
) -> BackupArchive:
    """The named archive, or the newest one."""

    if not archives:
        raise NotFoundError(f"There is no backup under {prefix} in the bucket.")

    if input_data.archive_key is None:
        return archives[-1]

    for archive in archives:
        if archive.key == input_data.archive_key:
            return archive

    raise NotFoundError(f"There is no backup {input_data.archive_key}.")
