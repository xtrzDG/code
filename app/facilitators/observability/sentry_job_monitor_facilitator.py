import logging
from collections.abc import Callable
from typing import Literal

from sentry_sdk.crons import capture_checkin
from sentry_sdk.crons.consts import MonitorStatus
from sentry_sdk.types import MonitorConfig

from app.contracts.observability import JobMonitorFacilitatorContract
from app.schemas.constants.observability import PeriodicJobOutcome
from app.schemas.dto.observability import JobCheckIn
from app.schemas.typings.platform.constrained_integers import JobIntervalSeconds
from app.schemas.typings.platform.constrained_strings import JobName
from app.schemas.typings.platform.strings import JobCheckInId

type CheckInCapture = Callable[..., str]

LOGGER: logging.Logger = logging.getLogger(__name__)
SECONDS_PER_MINUTE: int = 60
SECONDS_PER_HOUR: int = 60 * SECONDS_PER_MINUTE
SECONDS_PER_DAY: int = 24 * SECONDS_PER_HOUR
# A run may start this many minutes late before Sentry calls it missed:
# workers tick every WORKER_POLL_SECONDS and a failed run is retried after
# five minutes.
CHECKIN_MARGIN_MINUTES: int = 15
# A run still going after this long is reported as timed out.
MAX_RUNTIME_MINUTES: int = 60
OUTCOME_STATUSES: dict[PeriodicJobOutcome, str] = {
    PeriodicJobOutcome.SUCCEEDED: MonitorStatus.OK,
    PeriodicJobOutcome.FAILED: MonitorStatus.ERROR,
}


class SentryJobMonitorFacilitator(JobMonitorFacilitatorContract):
    """
    Sentry Crons check-ins around each periodic job run: "in progress" when
    it starts, "ok" or "error" when it ends. The monitor of a job (its slug
    is the job name) is created by the first check-in with the job's
    interval, so a job that stops running shows up as missed in Sentry.
    Needs Sentry initialized (SentryErrorReportingFacilitator).
    """

    def __init__(self, capture: CheckInCapture = capture_checkin) -> None:
        self._capture: CheckInCapture = capture

    def job_started(
        self,
        job_name: JobName,
        interval_seconds: JobIntervalSeconds,
    ) -> JobCheckIn:
        check_in = JobCheckIn(job_name=job_name, interval_seconds=interval_seconds)
        try:
            check_in_id: str = self._capture(
                monitor_slug=monitor_slug(job_name),
                status=MonitorStatus.IN_PROGRESS,
                monitor_config=build_monitor_config(interval_seconds),
            )
        except Exception:  # noqa: BLE001 - monitoring must never fail a job
            LOGGER.exception("Sentry check-in of %s failed", job_name)
            return check_in

        return check_in.model_copy(update={"check_in_id": JobCheckInId(check_in_id)})

    def job_finished(self, check_in: JobCheckIn, outcome: PeriodicJobOutcome) -> None:
        if check_in.check_in_id is None:
            return

        try:
            self._capture(
                monitor_slug=monitor_slug(check_in.job_name),
                check_in_id=str(check_in.check_in_id),
                status=OUTCOME_STATUSES[outcome],
            )
        except Exception:  # noqa: BLE001 - monitoring must never fail a job
            LOGGER.exception("Sentry check-in of %s failed", check_in.job_name)


def monitor_slug(job_name: JobName) -> str:
    """Sentry monitor slugs use hyphens: send_booking_reminders -> send-booking-reminders."""

    return str(job_name).replace("_", "-")


def build_monitor_config(interval_seconds: JobIntervalSeconds) -> MonitorConfig:
    """The job's interval in the largest whole unit Sentry accepts."""

    seconds: int = int(interval_seconds)
    unit: Literal["day", "hour", "minute"] = "minute"
    value: int = max(1, seconds // SECONDS_PER_MINUTE)
    if seconds % SECONDS_PER_DAY == 0:
        value, unit = seconds // SECONDS_PER_DAY, "day"
    elif seconds % SECONDS_PER_HOUR == 0:
        value, unit = seconds // SECONDS_PER_HOUR, "hour"

    return {
        "schedule": {"type": "interval", "value": value, "unit": unit},
        "checkin_margin": CHECKIN_MARGIN_MINUTES,
        "max_runtime": MAX_RUNTIME_MINUTES,
        "timezone": "UTC",
    }
