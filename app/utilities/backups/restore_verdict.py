"""
The restore drill's checks: does the restored database hold what the
backup recorded, does it match this checkout's schema, and does row-level
security still isolate businesses? Each failed check is one sentence that
names tables and counts only.
"""

from typed_time_provider import Microseconds

from app.schemas.dto.backups import (
    BackupManifest,
    DatabaseFacts,
    IsolationProbe,
    RecordedMigration,
    RestoredDatabase,
)
from app.schemas.dto.storage import SchemaMigrationScript
from app.schemas.typings.backups.constrained_integers import BackupFreshnessHours
from app.schemas.typings.backups.constrained_strings import DatabaseTableName
from app.schemas.typings.backups.strings import RestoreCheckProblem
from app.schemas.typings.storage.constrained_strings import SchemaMigrationName

MICROSECONDS_PER_HOUR: int = 3600 * 1_000_000
# The only table of the application schema without row-level security: the
# migration runner's record, which holds no business data.
UNSECURED_TABLES: frozenset[DatabaseTableName] = frozenset(
    {DatabaseTableName("workshop.schema_migrations")}
)


def judge_restore(
    manifest: BackupManifest,
    restored: RestoredDatabase,
    repository_migrations: list[SchemaMigrationScript],
) -> list[RestoreCheckProblem]:
    return [
        *compare_contents(manifest.facts, restored.facts),
        *compare_schema(restored.facts.applied_migrations, repository_migrations),
        *check_isolation(restored.facts, restored.isolation_probes),
    ]


def check_freshness(
    created_at: Microseconds,
    now: Microseconds,
    max_age: BackupFreshnessHours,
) -> list[RestoreCheckProblem]:
    age_hours: float = (int(now) - int(created_at)) / MICROSECONDS_PER_HOUR
    if age_hours <= int(max_age):
        return []

    return [
        problem(
            f"The newest backup is {age_hours:.0f} hours old (at most "
            f"{int(max_age)} allowed): the backup job has not run on time."
        )
    ]


def compare_contents(
    dumped: DatabaseFacts, restored: DatabaseFacts
) -> list[RestoreCheckProblem]:
    problems: list[RestoreCheckProblem] = []
    for table, count in sorted(dumped.row_counts.items()):
        restored_count = restored.row_counts.get(table)
        if restored_count is None:
            problems.append(problem(f"{table}: missing from the restored database."))
        elif int(restored_count) != int(count):
            problems.append(
                problem(
                    f"{table}: {int(restored_count)} rows restored, "
                    f"{int(count)} dumped."
                )
            )

    problems.extend(
        problem(f"{table}: restored but not in the backup's manifest.")
        for table in sorted(set(restored.row_counts) - set(dumped.row_counts))
    )
    if sorted(restored.secured_tables) != sorted(dumped.secured_tables):
        problems.append(
            problem(
                "Row-level security differs: "
                f"{len(restored.secured_tables)} secured tables restored, "
                f"{len(dumped.secured_tables)} dumped."
            )
        )
    if int(restored.policy_count) != int(dumped.policy_count):
        problems.append(
            problem(
                f"{int(restored.policy_count)} row-level security policies "
                f"restored, {int(dumped.policy_count)} dumped."
            )
        )
    if restored.applied_migrations != dumped.applied_migrations:
        problems.append(problem("The restored schema_migrations differ from the dump."))
    if not restored.applied_migrations or not restored.secured_tables:
        problems.append(
            problem("The restored database has no application schema at all.")
        )

    return problems


def compare_schema(
    applied: list[RecordedMigration],
    repository: list[SchemaMigrationScript],
) -> list[RestoreCheckProblem]:
    """
    Every migration of the backup must be one of this checkout's, with the
    same checksum; the checkout may be ahead (migrations newer than the
    backup's newest are pending, which a restore then applies).
    """

    known: dict[SchemaMigrationName, SchemaMigrationScript] = {
        script.name: script for script in repository
    }
    problems: list[RestoreCheckProblem] = []
    for migration in applied:
        script = known.get(migration.name)
        if script is None:
            problems.append(
                problem(
                    f"Migration {migration.name} is in the backup, not in the code."
                )
            )
        elif script.checksum != migration.checksum:
            problems.append(
                problem(f"Migration {migration.name} differs from the code's file.")
            )

    newest: str = max((str(migration.name) for migration in applied), default="")
    applied_names: set[SchemaMigrationName] = {migration.name for migration in applied}
    problems.extend(
        problem(f"Migration {script.name} is older than the backup but missing in it.")
        for script in repository
        if script.name not in applied_names and str(script.name) < newest
    )
    return problems


def pending_migrations(
    applied: list[RecordedMigration],
    repository: list[SchemaMigrationScript],
) -> list[SchemaMigrationName]:
    """This checkout's migrations newer than everything in the backup."""

    newest: str = max((str(migration.name) for migration in applied), default="")
    return [script.name for script in repository if str(script.name) > newest]


def check_isolation(
    restored: DatabaseFacts,
    probes: list[IsolationProbe],
) -> list[RestoreCheckProblem]:
    problems: list[RestoreCheckProblem] = [
        problem(f"{table}: row-level security is off (a business table without it).")
        for table in sorted(
            set(restored.row_counts) - set(restored.secured_tables) - UNSECURED_TABLES
        )
    ]
    probed = {probe.table for probe in probes}
    problems.extend(
        problem(f"{table}: row-level security was not probed.")
        for table in sorted(set(restored.secured_tables) - probed)
    )
    for probe in probes:
        if int(probe.unscoped_rows) > 0:
            problems.append(
                problem(
                    f"{probe.table}: {int(probe.unscoped_rows)} rows visible "
                    "without a business scope."
                )
            )
        if int(probe.foreign_rows) > 0:
            problems.append(
                problem(
                    f"{probe.table}: {int(probe.foreign_rows)} rows of other "
                    "businesses visible in one business's scope."
                )
            )
        if int(probe.own_rows) != int(probe.expected_own_rows):
            problems.append(
                problem(
                    f"{probe.table}: {int(probe.own_rows)} of the business's "
                    f"{int(probe.expected_own_rows)} rows visible in its scope."
                )
            )

    return problems


def problem(text: str) -> RestoreCheckProblem:
    return RestoreCheckProblem(text)
