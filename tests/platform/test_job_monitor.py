"""Sentry Crons check-ins around periodic jobs, and nothing without Sentry."""

from typing import Any

import pytest

from app.facilitators.observability.job_monitor_factory import (
    build_job_monitor_facilitator,
)
from app.facilitators.observability.null_job_monitor_facilitator import (
    NullJobMonitorFacilitator,
)
from app.facilitators.observability.sentry_error_reporting_facilitator import (
    SentryErrorReportingFacilitator,
)
from app.facilitators.observability.sentry_job_monitor_facilitator import (
    SentryJobMonitorFacilitator,
    build_monitor_config,
)
from app.schemas.constants.environment import DeploymentEnvironment
from app.schemas.constants.observability import PeriodicJobOutcome
from app.schemas.typings.platform.constrained_integers import JobIntervalSeconds
from app.schemas.typings.platform.constrained_strings import JobName
from app.schemas.typings.platform.strings import PlatformSecret

JOB: JobName = JobName("send_booking_reminders")


class RecordingCapture:
    def __init__(self, should_fail: bool = False) -> None:
        self.calls: list[dict[str, Any]] = []
        self._should_fail: bool = should_fail

    def __call__(self, **options: Any) -> str:
        if self._should_fail:
            raise ConnectionError("sentry is down")

        self.calls.append(options)
        return "check-in-1"


def test_a_run_checks_in_when_it_starts_and_when_it_ends() -> None:
    capture = RecordingCapture()
    monitor = SentryJobMonitorFacilitator(capture)

    check_in = monitor.job_started(JOB, JobIntervalSeconds(15 * 60))
    monitor.job_finished(check_in, PeriodicJobOutcome.SUCCEEDED)
    failed = monitor.job_started(JOB, JobIntervalSeconds(15 * 60))
    monitor.job_finished(failed, PeriodicJobOutcome.FAILED)

    assert capture.calls[0]["monitor_slug"] == "send-booking-reminders"
    assert capture.calls[0]["status"] == "in_progress"
    assert capture.calls[0]["monitor_config"]["schedule"] == {
        "type": "interval",
        "value": 15,
        "unit": "minute",
    }
    assert capture.calls[1] == {
        "monitor_slug": "send-booking-reminders",
        "check_in_id": "check-in-1",
        "status": "ok",
    }
    assert capture.calls[3]["status"] == "error"


@pytest.mark.parametrize(
    ("seconds", "schedule"),
    [
        (24 * 3600, {"type": "interval", "value": 1, "unit": "day"}),
        (7 * 24 * 3600, {"type": "interval", "value": 7, "unit": "day"}),
        (3600, {"type": "interval", "value": 1, "unit": "hour"}),
        (90, {"type": "interval", "value": 1, "unit": "minute"}),
        (30, {"type": "interval", "value": 1, "unit": "minute"}),
    ],
)
def test_the_interval_is_given_in_whole_units(
    seconds: int, schedule: dict[str, object]
) -> None:
    config: dict[str, Any] = dict(build_monitor_config(JobIntervalSeconds(seconds)))

    assert config["schedule"] == schedule
    assert config["timezone"] == "UTC"


def test_a_failing_monitor_never_fails_the_job(
    caplog: pytest.LogCaptureFixture,
) -> None:
    monitor = SentryJobMonitorFacilitator(RecordingCapture(should_fail=True))

    check_in = monitor.job_started(JOB, JobIntervalSeconds(3600))
    monitor.job_finished(check_in, PeriodicJobOutcome.SUCCEEDED)
    working = SentryJobMonitorFacilitator(RecordingCapture())
    broken_end = working.job_started(JOB, JobIntervalSeconds(3600))
    SentryJobMonitorFacilitator(RecordingCapture(should_fail=True)).job_finished(
        broken_end, PeriodicJobOutcome.FAILED
    )

    assert check_in.check_in_id is None
    assert caplog.text.count("Sentry check-in of send_booking_reminders failed") == 2


def ignore_options(**options: Any) -> None:
    del options


def test_the_monitor_follows_the_error_reporter() -> None:
    disabled = SentryErrorReportingFacilitator(
        dsn=None, environment=DeploymentEnvironment.TEST
    )
    enabled = SentryErrorReportingFacilitator(
        dsn=PlatformSecret("https://key@o1.ingest.de.sentry.io/1"),
        environment=DeploymentEnvironment.TEST,
        sentry_init=ignore_options,
    )
    null_monitor = build_job_monitor_facilitator(disabled)

    assert isinstance(null_monitor, NullJobMonitorFacilitator)
    assert isinstance(
        build_job_monitor_facilitator(enabled), SentryJobMonitorFacilitator
    )
    check_in = null_monitor.job_started(JOB, JobIntervalSeconds(60))
    null_monitor.job_finished(check_in, PeriodicJobOutcome.SUCCEEDED)
    assert check_in.check_in_id is None
