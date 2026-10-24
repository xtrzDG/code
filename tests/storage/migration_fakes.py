"""Fakes of the migration runner's source and store, and running it."""

from typed_time_provider import Microseconds

from app.contracts.storage import (
    MigrationRetryPauseContract,
    SchemaMigrationSourceAdapterContract,
    SchemaMigrationStoreAdapterContract,
)
from app.operators.pipeline_operator import PipelineOperator
from app.orchestrators.use_case_orchestrator import UseCaseOrchestrator
from app.pipelines.orchestrator_pipeline import OrchestratorPipeline
from app.schemas.dto.storage import (
    AppliedSchemaMigration,
    ApplyDatabaseMigrationsCommand,
    DatabaseMigrationsReport,
    SchemaMigrationScript,
)
from app.schemas.exceptions.storage_errors import MigrationLockTimeoutError
from app.schemas.typings.storage.constrained_integers import MigrationAttemptLimit
from app.schemas.typings.storage.constrained_strings import SchemaMigrationName
from app.schemas.typings.storage.strings import SchemaMigrationSql
from app.use_cases.maintenance.apply_database_migrations_use_case import (
    ApplyDatabaseMigrationsUseCase,
)
from app.utilities.storage.schema_migration_files import compute_migration_checksum
from tests.storage.storage_testing import (
    FIXED_NANOSECONDS,
    RecordedRetryPause,
    build_fixed_wall_clock,
)

NOW_MICROSECONDS: int = FIXED_NANOSECONDS // 1_000


def build_script(name: str, sql_text: str = "select 1;") -> SchemaMigrationScript:
    return SchemaMigrationScript(
        name=SchemaMigrationName(name),
        checksum=compute_migration_checksum(sql_text),
        sql=SchemaMigrationSql(sql_text),
    )


class FakeMigrationSource(SchemaMigrationSourceAdapterContract):
    def __init__(self, scripts: list[SchemaMigrationScript]) -> None:
        self.scripts: list[SchemaMigrationScript] = scripts

    def load_scripts(self) -> list[SchemaMigrationScript]:
        return list(self.scripts)


class FakeMigrationStore(SchemaMigrationStoreAdapterContract):
    """Records migrations in a dict; `raced` names are applied by "another runner"."""

    def __init__(
        self,
        raced_names: frozenset[str] = frozenset(),
        lock_timeouts: dict[str, int] | None = None,
    ) -> None:
        self.applied: dict[SchemaMigrationName, AppliedSchemaMigration] = {}
        self.executed_names: list[str] = []
        self.tries: list[str] = []
        self._raced_names: frozenset[str] = raced_names
        # How many tries of a script time out on a lock before one succeeds.
        self._lock_timeouts: dict[str, int] = dict(lock_timeouts or {})

    def list_applied(self) -> list[AppliedSchemaMigration]:
        return sorted(self.applied.values(), key=lambda migration: str(migration.name))

    def apply_if_pending(
        self,
        script: SchemaMigrationScript,
        applied_at: Microseconds,
    ) -> bool:
        self.tries.append(str(script.name))
        if self._lock_timeouts.get(str(script.name), 0) > 0:
            self._lock_timeouts[str(script.name)] -= 1
            raise MigrationLockTimeoutError("lock not available")

        if script.name in self._raced_names:
            return False

        self.executed_names.append(str(script.name))
        self.applied[script.name] = AppliedSchemaMigration(
            name=script.name,
            checksum=script.checksum,
            applied_at=applied_at,
        )
        return True


def run(
    source: FakeMigrationSource,
    store: FakeMigrationStore,
    is_dry_run: bool = False,
    retry_pause: MigrationRetryPauseContract | None = None,
    attempt_limit: int = 5,
) -> DatabaseMigrationsReport:
    operator = PipelineOperator(
        OrchestratorPipeline(
            UseCaseOrchestrator(
                ApplyDatabaseMigrationsUseCase(
                    migration_source=source,
                    migration_store=store,
                    wall_clock=build_fixed_wall_clock(),
                    retry_pause=retry_pause or RecordedRetryPause(),
                    attempt_limit=MigrationAttemptLimit(attempt_limit),
                )
            )
        )
    )
    return operator.operate(ApplyDatabaseMigrationsCommand(is_dry_run=is_dry_run))
