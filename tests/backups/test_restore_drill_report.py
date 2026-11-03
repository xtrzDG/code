"""
The restore drill measures itself (REL-03): it prints how long the
download, restore and checks took and how old the restored backup was,
and `--report` appends the same as a Markdown section to a file (the
workflow's run summary), failures included.
"""

from pathlib import Path

import pytest

from app.adapters.backup.age_backup_cipher_adapter import AgeBackupCipherAdapter
from app.adapters.storage.postgres.sql_file_migration_source_adapter import (
    SqlFileMigrationSourceAdapter,
)
from app.gateways.cli.restore_check import build_argument_parser
from app.gateways.cli.restore_drill_report import (
    append_report,
    describe_timings,
    duration,
    failure_report,
    markdown_report,
)
from app.schemas.dto.backups import RestoreCheckReport
from app.schemas.typings.backups.constrained_integers import BackupFreshnessHours
from app.use_cases.maintenance.backups.check_backup_restore_use_case import (
    CheckBackupRestoreUseCase,
)
from tests.backups.backup_fakes import (
    PREFIX,
    FakeScratchDatabase,
    InMemoryBackupBucket,
    clock_at,
    moment,
)
from tests.backups.test_backup_use_cases import (
    IDENTITY,
    MIGRATION_SQL,
    command,
    facts,
    take_backup,
)


@pytest.fixture
def report(tmp_path: Path) -> RestoreCheckReport:
    migrations = tmp_path / "migrations"
    migrations.mkdir()
    (migrations / "0001_document_collections.sql").write_text(MIGRATION_SQL)
    bucket = InMemoryBackupBucket()
    take_backup(bucket, tmp_path, "2026-10-03T01:07:00")
    return CheckBackupRestoreUseCase(
        backup_bucket=bucket,
        backup_cipher=AgeBackupCipherAdapter([], IDENTITY),
        scratch_database=FakeScratchDatabase(facts()),
        migration_source=SqlFileMigrationSourceAdapter(migrations),
        wall_clock=clock_at("2026-10-03T02:00:00"),
        prefix=PREFIX,
        max_age=BackupFreshnessHours(26),
    ).run(command(tmp_path))


def test_the_drill_says_how_long_it_took_and_how_old_the_backup_was(
    report: RestoreCheckReport,
) -> None:
    line = describe_timings(
        report, moment("2026-10-03T02:00:00"), moment("2026-10-03T02:04:12")
    )

    assert "download, restore and checks took 4 min 12 s" in line
    assert "the backup was 53 min 00 s old when the drill began" in line


def test_the_markdown_report_records_the_timings_and_the_verdict(
    report: RestoreCheckReport,
) -> None:
    text = markdown_report(
        report, False, moment("2026-10-03T02:00:00"), moment("2026-10-03T04:05:00")
    )

    assert text.startswith("### Restore drill 2026-10-03 02:00:00 UTC: passed")
    assert "| Backup taken | 2026-10-03 01:07:00 UTC |" in text
    assert "| Drill finished | 2026-10-03 04:05:00 UTC |" in text
    assert "| Download, restore and checks took | 2 h 05 min |" in text
    assert "| Failed checks | 0 |" in text
    assert "OK: the backup restores completely and isolates businesses." in text


def test_reports_are_appended_failures_included(
    report: RestoreCheckReport, tmp_path: Path
) -> None:
    summary = tmp_path / "summary.md"
    summary.write_text("## Earlier step\n", encoding="utf-8")
    started = moment("2026-10-05T03:41:00")

    append_report(summary, markdown_report(report, True, started, started))
    append_report(summary, failure_report("the bucket refused the key", started))

    text = summary.read_text(encoding="utf-8")
    assert text.startswith("## Earlier step\n### Restore drill")
    assert "(kept)." in text
    assert "### Restore drill 2026-10-05 03:41:00 UTC: failed" in text
    assert "Restore drill failed: the bucket refused the key" in text


def test_durations_read_in_the_largest_units() -> None:
    assert duration(9_000_000) == "9 s"
    assert duration(252_000_000) == "4 min 12 s"
    assert duration(7_500_000_000) == "2 h 05 min"
    assert duration(-5) == "0 s"


def test_the_command_takes_a_report_file() -> None:
    parser = build_argument_parser()

    assert parser.parse_args([]).report is None
    assert parser.parse_args(["--report", "summary.md"]).report == "summary.md"
