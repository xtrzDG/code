"""The restore drill's checks, one failure at a time."""

from app.schemas.dto.backups import (
    BackupManifest,
    DatabaseFacts,
    IsolationProbe,
    RestoredDatabase,
)
from app.schemas.dto.storage import SchemaMigrationScript
from app.schemas.typings.backups.constrained_integers import (
    BackupArchiveSize,
    BackupFreshnessHours,
    DatabasePolicyCount,
    TableRowCount,
)
from app.schemas.typings.backups.constrained_strings import (
    BackupChecksum,
    BackupObjectKey,
    DatabaseTableName,
    ScratchDatabaseName,
)
from app.schemas.typings.storage.constrained_strings import (
    SchemaMigrationChecksum,
    SchemaMigrationName,
)
from app.schemas.typings.storage.strings import SchemaMigrationSql
from app.utilities.backups.restore_verdict import (
    check_freshness,
    judge_restore,
    pending_migrations,
)
from tests.backups.backup_fakes import CHECKSUM, build_facts, clean_probes, moment

BOOKINGS = DatabaseTableName("workshop.bookings")


def script(
    name: str, checksum: SchemaMigrationChecksum = CHECKSUM
) -> SchemaMigrationScript:
    return SchemaMigrationScript(
        name=SchemaMigrationName(name), checksum=checksum, sql=SchemaMigrationSql("")
    )


def manifest_of(facts: DatabaseFacts) -> BackupManifest:
    return BackupManifest(
        archive_key=BackupObjectKey("workshop/2026/10/20261003T010700Z.pgdump.age"),
        created_at=moment("2026-10-03T01:07:00"),
        archive_size=BackupArchiveSize(10),
        archive_checksum=BackupChecksum("b" * 64),
        facts=facts,
    )


def restored_with(
    facts: DatabaseFacts, probes: list[IsolationProbe] | None = None
) -> RestoredDatabase:
    return RestoredDatabase(
        scratch_database=ScratchDatabaseName("restore_drill_test"),
        facts=facts,
        isolation_probes=clean_probes(facts) if probes is None else probes,
    )


def judge(
    dumped: DatabaseFacts,
    restored: RestoredDatabase,
    repository: list[SchemaMigrationScript] | None = None,
) -> list[str]:
    scripts = (
        [script("0001_document_collections")] if repository is None else repository
    )
    return [
        str(problem)
        for problem in judge_restore(manifest_of(dumped), restored, scripts)
    ]


def test_an_identical_restore_passes() -> None:
    facts = build_facts()

    assert judge(facts, restored_with(facts)) == []


def test_lost_extra_and_missing_rows_and_tables_are_named() -> None:
    dumped = build_facts(bookings=5)
    counts = dict(build_facts(bookings=4).row_counts)
    del counts[DatabaseTableName("workshop.businesses")]
    counts[DatabaseTableName("workshop.strays")] = TableRowCount(1)
    restored = dumped.model_copy(update={"row_counts": counts})

    assert judge(dumped, restored_with(restored)) == [
        "workshop.bookings: 4 rows restored, 5 dumped.",
        "workshop.businesses: missing from the restored database.",
        "workshop.strays: restored but not in the backup's manifest.",
        "workshop.strays: row-level security is off (a business table without it).",
    ]


def test_lost_row_level_security_and_policies_fail() -> None:
    dumped = build_facts()
    restored = dumped.model_copy(
        update={
            "secured_tables": [BOOKINGS],
            "policy_count": DatabasePolicyCount(1),
        }
    )

    problems = judge(dumped, restored_with(restored))

    assert problems == [
        "Row-level security differs: 1 secured tables restored, 2 dumped.",
        "1 row-level security policies restored, 2 dumped.",
        "workshop.businesses: row-level security is off (a business table without it).",
    ]


def test_an_empty_database_is_no_backup() -> None:
    empty = DatabaseFacts()

    assert "The restored database has no application schema at all." in judge(
        empty, restored_with(empty)
    )


def test_migrations_must_match_the_checkout() -> None:
    restored = build_facts(migrations=("0001_document_collections", "0002_channels"))
    repository = [
        script("0001_document_collections", SchemaMigrationChecksum("c" * 64)),
        script("0003_later"),
    ]

    problems = judge(restored, restored_with(restored), repository)

    assert problems == [
        "Migration 0001_document_collections differs from the code's file.",
        "Migration 0002_channels is in the backup, not in the code.",
    ]


def test_a_gap_in_the_migrations_fails_but_newer_ones_are_pending() -> None:
    restored = build_facts(migrations=("0001_document_collections", "0003_third"))
    repository = [
        script("0001_document_collections"),
        script("0002_second"),
        script("0003_third"),
        script("0004_fourth"),
    ]

    assert judge(restored, restored_with(restored), repository) == [
        "Migration 0002_second is older than the backup but missing in it."
    ]
    assert pending_migrations(restored.applied_migrations, repository) == [
        SchemaMigrationName("0004_fourth")
    ]


def test_isolation_failures_are_reported_per_table() -> None:
    facts = build_facts()
    leaky = IsolationProbe(
        table=BOOKINGS,
        unscoped_rows=TableRowCount(2),
        own_rows=TableRowCount(1),
        expected_own_rows=TableRowCount(3),
        foreign_rows=TableRowCount(4),
    )

    assert judge(facts, restored_with(facts, [leaky])) == [
        "workshop.businesses: row-level security was not probed.",
        "workshop.bookings: 2 rows visible without a business scope.",
        "workshop.bookings: 4 rows of other businesses visible in one "
        "business's scope.",
        "workshop.bookings: 1 of the business's 3 rows visible in its scope.",
    ]


def test_freshness_allows_a_day_and_two_hours() -> None:
    created = moment("2026-10-02T01:07:00")

    assert (
        check_freshness(
            created, moment("2026-10-03T03:07:00"), BackupFreshnessHours(26)
        )
        == []
    )
    assert [
        str(problem)
        for problem in check_freshness(
            created, moment("2026-10-04T01:07:00"), BackupFreshnessHours(26)
        )
    ] == [
        "The newest backup is 48 hours old (at most 26 allowed): the backup job "
        "has not run on time."
    ]
