"""
The migration rehearsal (scripts/migration_rehearsal.py, REL-08): the
pending migrations are the files production's `release` commit lacks (the
newest three without it), the synthetic dataset fills production's biggest
tables in proportion, each pending file is timed alone, a slow or failing
one fails the run, and the perf workflow runs it every week.
"""

import json
from pathlib import Path
from typing import Any, cast

import yaml

from scripts.migration_rehearsal import dataset_size, rehearse
from scripts.migration_rehearsal_plan import (
    SCALES,
    DatasetSize,
    MigrationTiming,
    RehearsalReport,
    migration_names,
    names_at_ref,
    plan_rehearsal,
)
from scripts.migration_rehearsal_seed import seed_statements
from tests.storage.postgres_server import ThrowawayPostgresServer
from tests.storage.storage_testing import MIGRATIONS_DIRECTORY

ROOT: Path = Path(__file__).resolve().parents[2]
NAMES: list[str] = ["0001_a", "0002_b", "0003_c", "0004_d"]


def test_pending_migrations_are_those_production_lacks() -> None:
    plan = plan_rehearsal(NAMES, ["0001_a", "0002_b", "0009_gone"], "origin/release")

    assert plan.released == ["0001_a", "0002_b"]
    assert plan.pending == ["0003_c", "0004_d"]
    assert plan.base == "origin/release"


def test_without_the_release_ref_the_newest_files_are_pending() -> None:
    plan = plan_rehearsal(NAMES, None, "origin/release", fallback_pending=3)

    assert plan.released == ["0001_a"]
    assert plan.pending == ["0002_b", "0003_c", "0004_d"]
    assert names_at_ref("no-such-ref-anywhere") is None


def test_the_full_scale_is_production_sized_and_overridable() -> None:
    full: DatasetSize = SCALES["full"]

    assert (full.businesses, full.messages) == (500, 2_000_000)
    assert full.per_table["bookings"] == 200_000
    assert dataset_size("small", 1000, 3) == DatasetSize(businesses=3, messages=1000)


def test_the_seed_fills_only_tables_the_schema_has() -> None:
    statements = seed_statements({"messages": 10, "bookings": 2}, 4, {"messages"})

    assert statements[0] == "select set_config('app.bypass_rls', 'on', false)"
    assert len(statements) == 3
    assert "insert into workshop.messages" in statements[1]
    assert "generate_series(1, 10)" in statements[1]
    assert "'business_' || (n % 4)" in statements[1]
    assert statements[2] == "analyze workshop.messages"


def test_a_slow_or_failed_migration_fails_the_report() -> None:
    report = RehearsalReport(
        base="origin/release",
        scale="small",
        rows={"messages": 10},
        seed_seconds=1.0,
        budget_seconds=5.0,
        timings=[
            MigrationTiming("0003_c", 0.5),
            MigrationTiming("0004_d", 9.0),
            MigrationTiming("0005_e", 0.1, error="lock timeout"),
        ],
    )

    assert report.failures == [
        "0004_d took 9.0 s (budget 5 s)",
        "0005_e failed: lock timeout",
    ]
    assert json.loads(report.to_json())["failures"] == report.failures
    markdown = report.to_markdown()
    assert "| 0003_c | 0.50 | ok |" in markdown
    assert "| 0004_d | 9.00 | **over budget** |" in markdown
    assert "| 0005_e | 0.10 | **failed** |" in markdown


def test_nothing_pending_is_said_so() -> None:
    report = RehearsalReport("origin/release", "full", {}, 0.0, 300.0)

    assert report.failures == []
    assert "No pending migration" in report.to_markdown()


def test_the_rehearsal_times_each_pending_migration_on_a_seeded_copy(
    postgres_server: ThrowawayPostgresServer,
) -> None:
    names: list[str] = migration_names(MIGRATIONS_DIRECTORY)
    plan = plan_rehearsal(names, names[:-2], "test")

    report = rehearse(
        postgres_server,
        plan,
        DatasetSize(businesses=3, messages=200),
        "small",
        300.0,
        MIGRATIONS_DIRECTORY,
    )

    assert [timing.name for timing in report.timings] == names[-2:]
    assert report.failures == []
    assert report.rows["messages"] == 200


def test_the_perf_workflow_rehearses_against_the_release_branch() -> None:
    workflow = cast(
        dict[str, Any],
        yaml.safe_load(
            (ROOT / ".github" / "workflows" / "perf.yml").read_text(encoding="utf-8")
        ),
    )
    job = cast(dict[str, Any], workflow["jobs"]["migrations"])
    script = "\n".join(str(step.get("run", "")) for step in job["steps"])

    assert "scripts.migration_rehearsal --base-ref origin/release" in script
    assert '--scale "$PERF_SCALE"' in script
    checkout = job["steps"][0]
    assert checkout["with"]["fetch-depth"] == 0
