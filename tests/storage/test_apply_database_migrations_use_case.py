"""The migration use case with fake source and store (no database)."""

import pytest

from app.schemas.exceptions.application_errors import ConflictError
from tests.storage.migration_fakes import (
    NOW_MICROSECONDS,
    FakeMigrationSource,
    FakeMigrationStore,
    build_script,
    run,
)


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
