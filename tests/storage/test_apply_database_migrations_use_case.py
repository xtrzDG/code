"""The migration use case with fake source and store (no database)."""

import pytest
from typed_time_provider import Microseconds

from app.contracts.storage import (
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
from app.schemas.exceptions.application_errors import ConflictError
from app.schemas.typings.storage.constrained_strings import SchemaMigrationName
from app.schemas.typings.storage.strings import SchemaMigrationSql
from app.use_cases.maintenance.apply_database_migrations_use_case import (
    ApplyDatabaseMigrationsUseCase,
)
from app.utilities.storage.schema_migration_files import compute_migration_checksum
from tests.storage.storage_testing import FIXED_NANOSECONDS, build_fixed_wall_clock

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

    def __init__(self, raced_names: frozenset[str] = frozenset()) -> None:
        self.applied: dict[SchemaMigrationName, AppliedSchemaMigration] = {}
        self.executed_names: list[str] = []
        self._raced_names: frozenset[str] = raced_names

    def list_applied(self) -> list[AppliedSchemaMigration]:
        return sorted(self.applied.values(), key=lambda migration: str(migration.name))

    def apply_if_pending(
        self,
        script: SchemaMigrationScript,
        applied_at: Microseconds,
    ) -> bool:
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
) -> DatabaseMigrationsReport:
    operator = PipelineOperator(
        OrchestratorPipeline(
            UseCaseOrchestrator(
                ApplyDatabaseMigrationsUseCase(
                    migration_source=source,
                    migration_store=store,
                    wall_clock=build_fixed_wall_clock(),
                )
            )
        )
    )
    return operator.operate(ApplyDatabaseMigrationsCommand(is_dry_run=is_dry_run))


def test_pending_scripts_run_in_order_once() -> None:
    source = FakeMigrationSource(
        [build_script("0001_first"), build_script("0002_second")]
    )
    store = FakeMigrationStore()

    first_report = run(source, store)
    second_report = run(source, store)

    assert store.executed_names == ["0001_first", "0002_second"]
    assert first_report.newly_applied == ["0001_first", "0002_second"]
    assert second_report.newly_applied == []
    assert second_report.already_applied == ["0001_first", "0002_second"]
    assert {migration.applied_at for migration in store.list_applied()} == {
        NOW_MICROSECONDS
    }


def test_new_script_is_applied_after_earlier_ones() -> None:
    source = FakeMigrationSource([build_script("0001_first")])
    store = FakeMigrationStore()
    run(source, store)
    source.scripts.append(build_script("0002_added_later"))

    report = run(source, store)

    assert report.already_applied == ["0001_first"]
    assert report.newly_applied == ["0002_added_later"]


def test_dry_run_changes_nothing() -> None:
    source = FakeMigrationSource([build_script("0001_first")])
    store = FakeMigrationStore()

    report = run(source, store, is_dry_run=True)

    assert report.pending == ["0001_first"]
    assert report.newly_applied == []
    assert store.executed_names == []


def test_edited_applied_script_is_a_conflict_before_anything_runs() -> None:
    source = FakeMigrationSource([build_script("0001_first", "select 1;")])
    store = FakeMigrationStore()
    run(source, store)
    source.scripts = [
        build_script("0001_first", "select 2;"),
        build_script("0002_second"),
    ]

    with pytest.raises(ConflictError, match="0001_first"):
        run(source, store)

    assert store.executed_names == ["0001_first"]


def test_reused_version_is_a_conflict() -> None:
    source = FakeMigrationSource([build_script("0001_first")])
    store = FakeMigrationStore()
    run(source, store)
    source.scripts = [build_script("0001_renamed")]

    with pytest.raises(ConflictError, match="reuses version 0001"):
        run(source, store)


def test_unknown_applied_migrations_are_reported_not_undone() -> None:
    store = FakeMigrationStore()
    run(
        FakeMigrationSource([build_script("0001_first"), build_script("0002_newer")]),
        store,
    )

    report = run(FakeMigrationSource([build_script("0001_first")]), store)

    assert report.unknown_applied == ["0002_newer"]
    assert report.already_applied == ["0001_first"]


def test_script_applied_by_a_concurrent_runner_counts_as_already_applied() -> None:
    store = FakeMigrationStore(raced_names=frozenset({"0002_second"}))

    report = run(
        FakeMigrationSource([build_script("0001_first"), build_script("0002_second")]),
        store,
    )

    assert report.newly_applied == ["0001_first"]
    assert report.already_applied == ["0002_second"]
