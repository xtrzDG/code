"""The CLIs' configuration checks, monitoring and summaries."""

import io
from collections.abc import Callable, Mapping, Sequence
from typing import TextIO

import pytest

from app.gateways.cli import backup, restore_check
from app.gateways.cli.backup_wiring import MonitoredRun
from app.schemas.constants.observability import PeriodicJobOutcome
from app.schemas.dto.observability import JobCheckIn
from app.schemas.typings.platform.constrained_integers import JobIntervalSeconds
from app.schemas.typings.platform.constrained_strings import JobName
from app.utilities.security.age.age_keys import generate_identity, recipient_of
from tests.backups.test_backup_settings import BUCKET


class FakeReporter:
    def __init__(self) -> None:
        self.errors: list[BaseException] = []

    def capture_exception(self, error: BaseException) -> None:
        self.errors.append(error)


class FakeMonitor:
    def __init__(self) -> None:
        self.outcomes: list[PeriodicJobOutcome] = []

    def job_started(
        self, job_name: JobName, interval_seconds: JobIntervalSeconds
    ) -> JobCheckIn:
        return JobCheckIn(job_name=job_name, interval_seconds=interval_seconds)

    def job_finished(self, check_in: JobCheckIn, outcome: PeriodicJobOutcome) -> None:
        del check_in
        self.outcomes.append(outcome)


type Command = Callable[
    [Sequence[str] | None, Mapping[str, str] | None, TextIO | None, TextIO | None],
    int,
]


def run(command: Command, environment: dict[str, str]) -> tuple[int, str]:
    errors = io.StringIO()
    exit_code: int = command([], environment, io.StringIO(), errors)
    return exit_code, errors.getvalue()


@pytest.mark.parametrize("command", [backup.main, restore_check.main])
def test_invalid_settings_exit_with_2(command: Command) -> None:
    exit_code, errors = run(command, {"BACKUP_KEEP_DAILY": "many"})

    assert exit_code == 2
    assert "Invalid settings: BACKUP_KEEP_DAILY must be an integer" in errors


def test_the_backup_needs_a_database_and_a_bucket() -> None:
    exit_code, errors = run(backup.main, {"DATABASE_URL": "postgresql://x/y"})

    assert exit_code == 2
    assert "Backups are not configured" in errors


def test_the_drill_needs_the_identity_and_a_scratch_server() -> None:
    environment = {
        **BUCKET,
        "BACKUP_AGE_PUBLIC_KEY": str(recipient_of(generate_identity())),
    }

    exit_code, errors = run(restore_check.main, environment)

    assert exit_code == 2
    assert "BACKUP_AGE_IDENTITY and RESTORE_CHECK_DATABASE_URL" in errors


def test_a_monitored_run_checks_in_and_reports_failures() -> None:
    reporter, monitor = FakeReporter(), FakeMonitor()
    monitored = MonitoredRun(
        JobName("restore_drill"), JobIntervalSeconds(604800), reporter, monitor
    )

    assert monitored.run(lambda: ["problem"], lambda problems: not problems) == [
        "problem"
    ]
    assert monitored.run(lambda: [], lambda problems: not problems) == []
    with pytest.raises(RuntimeError, match="disk full"):
        monitored.run(raise_disk_full, lambda _result: True)

    assert monitor.outcomes == [
        PeriodicJobOutcome.FAILED,
        PeriodicJobOutcome.SUCCEEDED,
        PeriodicJobOutcome.FAILED,
    ]
    assert [str(error) for error in reporter.errors] == ["disk full"]


def raise_disk_full() -> list[str]:
    raise RuntimeError("disk full")
