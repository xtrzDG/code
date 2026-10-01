from typed_time_provider import Microseconds, WallClock

from app.contracts.storage import (
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
from app.schemas.exceptions.application_errors import ConflictError
from app.schemas.typings.storage.constrained_strings import SchemaMigrationName
from app.utilities.storage.schema_migration_files import migration_version


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
    """

    def __init__(
        self,
        migration_source: SchemaMigrationSourceAdapterContract,
        migration_store: SchemaMigrationStoreAdapterContract,
        wall_clock: WallClock[Microseconds],
    ) -> None:
        self._migration_source: SchemaMigrationSourceAdapterContract = migration_source
        self._migration_store: SchemaMigrationStoreAdapterContract = migration_store
        self._wall_clock: WallClock[Microseconds] = wall_clock

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
            if self._migration_store.apply_if_pending(
                script,
                self._wall_clock.now_unix(),
            ):
                newly_applied.append(script.name)
            else:
                already_applied.append(script.name)

        return DatabaseMigrationsReport(
            already_applied=already_applied,
            newly_applied=newly_applied,
            unknown_applied=unknown_applied,
        )


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
