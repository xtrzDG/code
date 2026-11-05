"""
What the restore drill prints and writes: the verdict (`describe_drill`),
its timings (`describe_timings`: how long the restore and its checks took,
and how old the restored backup was when the drill began, the data a
restore at that moment would lose) and the Markdown report `--report`
appends to a file. The workflow appends it to its run summary, the record
the restore-test report of docs/operations/restore-test-report.md quotes.
"""

from datetime import UTC, datetime
from pathlib import Path

from typed_time_provider import Microseconds

from app.schemas.dto.backups import RestoreCheckReport
from app.utilities.backups.backup_keys import to_datetime

MICROSECONDS_PER_SECOND: int = 1_000_000
SECONDS_PER_MINUTE: int = 60
MINUTES_PER_HOUR: int = 60


def describe_drill(report: RestoreCheckReport, is_kept: bool) -> str:
    facts = report.restored.facts
    taken: str = to_datetime(report.archive_created_at).strftime("%Y-%m-%d %H:%M UTC")
    lines: list[str] = [
        f"Restored {report.archive_key} (taken {taken}) into "
        f"{report.restored.scratch_database}"
        + (" (kept)." if is_kept else " (dropped again)."),
        f"{len(facts.row_counts)} tables, "
        f"{sum(int(count) for count in facts.row_counts.values())} rows, "
        f"{len(facts.applied_migrations)} migrations; row-level security "
        f"probed on {len(report.restored.isolation_probes)} tables.",
    ]
    ledger = report.restored.ledger
    if ledger is not None:
        lines.append(
            f"Deletion ledger: {int(ledger.deleted_businesses)} deleted businesses, "
            f"{int(ledger.erased_rows)} of their rows deleted again, "
            f"{int(ledger.remaining_rows)} left."
        )
        lines.append(
            f"Erasure ledger: {int(ledger.erased_contacts)} erased customers, "
            f"{int(ledger.restored_contacts)} of them with their data in this "
            "backup (reapply_contact_erasures erases them again after a restore)."
        )
    if report.pending_migrations:
        lines.append(
            f"{len(report.pending_migrations)} migrations of this checkout are "
            "newer than the backup: "
            + ", ".join(str(name) for name in report.pending_migrations)
        )
    lines.extend(f"FAILED  {problem}" for problem in report.problems)
    lines.append(
        f"{len(report.problems)} checks failed."
        if report.problems
        else "OK: the backup restores completely and isolates businesses."
    )
    return "\n".join(lines)


def describe_timings(
    report: RestoreCheckReport, started_at: Microseconds, finished_at: Microseconds
) -> str:
    """The measured restore time and the restored backup's age, one line."""

    return (
        f"Timings: download, restore and checks took "
        f"{duration(int(finished_at) - int(started_at))}; the backup was "
        f"{duration(int(started_at) - int(report.archive_created_at))} old when "
        "the drill began (the data a restore at that moment would lose)."
    )


def markdown_report(
    report: RestoreCheckReport,
    is_kept: bool,
    started_at: Microseconds,
    finished_at: Microseconds,
) -> str:
    """The drill as a Markdown section: when, how long, what it found."""

    verdict: str = "failed" if report.problems else "passed"
    return "\n".join(
        [
            f"### Restore drill {moment(started_at)}: {verdict}",
            "",
            "| Measure | Value |",
            "| --- | --- |",
            f"| Archive | `{report.archive_key}` |",
            f"| Backup taken | {moment(report.archive_created_at)} |",
            f"| Drill started | {moment(started_at)} |",
            f"| Drill finished | {moment(finished_at)} |",
            "| Download, restore and checks took | "
            f"{duration(int(finished_at) - int(started_at))} |",
            "| Backup age at the start (data a restore would lose) | "
            f"{duration(int(started_at) - int(report.archive_created_at))} |",
            f"| Failed checks | {len(report.problems)} |",
            "",
            "```",
            describe_drill(report, is_kept),
            "```",
            "",
        ]
    )


def failure_report(error: str, started_at: Microseconds) -> str:
    """A drill that stopped before its checks: when, and why."""

    return "\n".join(
        [
            f"### Restore drill {moment(started_at)}: failed",
            "",
            "```",
            f"Restore drill failed: {error}",
            "```",
            "",
        ]
    )


def append_report(path: Path, text: str) -> None:
    """Appends a report (the workflow's summary file may hold others)."""

    with path.open("a", encoding="utf-8") as report_file:
        report_file.write(text + "\n")


def duration(microseconds: int) -> str:
    """'2 h 05 min', '4 min 12 s' or '9 s' (never negative)."""

    seconds: int = max(microseconds, 0) // MICROSECONDS_PER_SECOND
    minutes, seconds = divmod(seconds, SECONDS_PER_MINUTE)
    hours, minutes = divmod(minutes, MINUTES_PER_HOUR)
    if hours:
        return f"{hours} h {minutes:02d} min"
    if minutes:
        return f"{minutes} min {seconds:02d} s"
    return f"{seconds} s"


def moment(at: Microseconds) -> str:
    return datetime.fromtimestamp(int(at) / MICROSECONDS_PER_SECOND, UTC).strftime(
        "%Y-%m-%d %H:%M:%S UTC"
    )
