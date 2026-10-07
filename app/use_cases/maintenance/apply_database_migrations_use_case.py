import logging

from typed_time_provider import Microseconds, WallClock

from app.contracts.storage import (
    MigrationRetryPauseContract,
    SchemaMigrationSourceAdapterContract,
    SchemaMigrationStoreAdapterContract,
)
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.dto.storage import (
    AppliedSchemaMigration,
    ApplyDatabaseMigrationsCommand,
    DatabaseMigrationsReport,
    SchemaMigrationScript,
)
from app.schemas.exceptions.application_errors import (
    ConflictError,
    ExternalServiceError,
)
from app.schemas.exceptions.storage_errors import MigrationLockTimeoutError
from app.schemas.typings.storage.constrained_integers import (
    MigrationAttemptLimit,
    MigrationAttemptNumber,
)
from app.schemas.typings.storage.constrained_strings import SchemaMigrationName
from app.utilities.storage.schema_migration_files import migration_version

DEFAULT_ATTEMPT_LIMIT: MigrationAttemptLimit = MigrationAttemptLimit(5)
logger: logging.Logger = logging.getLogger(__name__)


class ApplyDatabaseMigrationsUseCase(
    UseCaseContract[ApplyDatabaseMigrationsCommand, DatabaseMigrationsReport]
):
    """
    Bring the database schema up to date with the migration files.

    Pending scripts run in version order, each in its own transaction;
    running again applies nothing (idempotent), and concurrent runners apply
    every script once. Before anything runs, the files are checked against
    the database: an applied script whose content changed, or a new script
    that reuses the version of an applied one, is a ConflictError. Scripts
    recorded in the database but missing from the files (applied by a newer
    release) are reported and left alone. A dry run only lists what is
    pending.

    A script that waited too long for a lock (the live release kept its
    table busy) was rolled back by the store; it is tried again after a
    growing, jittered pause, up to `attempt_limit` tries, and only then
    fails the run (and the deploy), which is safe to start again.
    """

    def __init__(
        self,
        migration_source: SchemaMigrationSourceAdapterContract,
        migration_store: SchemaMigrationStoreAdapterContract,
        wall_clock: WallClock[Microseconds],
        retry_pause: MigrationRetryPauseContract,
        attempt_limit: MigrationAttemptLimit = DEFAULT_ATTEMPT_LIMIT,
    ) -> None:
        self._migration_source: SchemaMigrationSourceAdapterContract = migration_source
        self._migration_store: SchemaMigrationStoreAdapterContract = migration_store
        self._wall_clock: WallClock[Microseconds] = wall_clock
        self._retry_pause: MigrationRetryPauseContract = retry_pause
        self._attempt_limit: MigrationAttemptLimit = attempt_limit

    def run(
        self,
        input_data: ApplyDatabaseMigrationsCommand,
    ) -> DatabaseMigrationsReport:
        scripts: list[SchemaMigrationScript] = self._migration_source.load_scripts()
        applied_by_name: dict[SchemaMigrationName, AppliedSchemaMigration] = {
            migration.name: migration
            for migration in self._migration_store.list_applied()
        }
        require_unchanged_applied_scripts(scripts, applied_by_name)
        pending_scripts: list[SchemaMigrationScript] = [
            script for script in scripts if script.name not in applied_by_name
        ]
        require_unused_versions(pending_scripts, applied_by_name)

        already_applied: list[SchemaMigrationName] = [
            script.name for script in scripts if script.name in applied_by_name
        ]
        script_names: set[SchemaMigrationName] = {script.name for script in scripts}
        unknown_applied: list[SchemaMigrationName] = sorted(
            migration_name
            for migration_name in applied_by_name
            if migration_name not in script_names
        )
        if input_data.is_dry_run:
            return DatabaseMigrationsReport(
                already_applied=already_applied,
                pending=[script.name for script in pending_scripts],
                unknown_applied=unknown_applied,
            )

        newly_applied: list[SchemaMigrationName] = []
        for script in pending_scripts:
            if self._apply_with_retries(script):
                newly_applied.append(script.name)
            else:
                already_applied.append(script.name)

        return DatabaseMigrationsReport(
            already_applied=already_applied,
            newly_applied=newly_applied,
            unknown_applied=unknown_applied,
        )

    def _apply_with_retries(self, script: SchemaMigrationScript) -> bool:
        """
        Raises:
            ExternalServiceError: every try waited too long for a lock, or
                the script failed.
        """

        attempt: int = 1
        while True:
            try:
                return self._migration_store.apply_if_pending(
                    script, self._wall_clock.now_unix()
                )
            except MigrationLockTimeoutError as error:
                if attempt >= int(self._attempt_limit):
                    raise ExternalServiceError(
                        f"Migration {str(script.name)!r} gave up after "
                        f"{attempt} tries: {error}"
                    ) from error

                logger.warning(
                    "Migration %s, try %d of %d: %s Trying again.",
                    script.name,
                    attempt,
                    int(self._attempt_limit),
                    error,
                )
                self._retry_pause.pause(MigrationAttemptNumber(attempt))
                attempt += 1


def require_unchanged_applied_scripts(
    scripts: list[SchemaMigrationScript],
    applied_by_name: dict[SchemaMigrationName, AppliedSchemaMigration],
) -> None:
    for script in scripts:
        applied_migration: AppliedSchemaMigration | None = applied_by_name.get(
            script.name
        )
        if applied_migration is None or applied_migration.checksum == script.checksum:
            continue

        raise ConflictError(
            f"Migration {str(script.name)!r} changed after it was applied; "
            "never edit an applied migration, add a new one."
        )


def require_unused_versions(
    pending_scripts: list[SchemaMigrationScript],
    applied_by_name: dict[SchemaMigrationName, AppliedSchemaMigration],
) -> None:
    applied_versions: dict[str, SchemaMigrationName] = {
        migration_version(migration_name): migration_name
        for migration_name in applied_by_name
    }
    for script in pending_scripts:
        applied_name: SchemaMigrationName | None = applied_versions.get(
            migration_version(script.name)
        )
        if applied_name is None:
            continue

        raise ConflictError(
            f"Migration {str(script.name)!r} reuses version "
            f"{migration_version(script.name)} of the applied migration "
            f"{str(applied_name)!r}; give it the next free version."
        )
