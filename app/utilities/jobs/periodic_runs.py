"""
Periods of periodic jobs and the rule that decides when a run may start.

A periodic job runs once per period, shared by every worker: the date of a
daily job, the ISO week of a weekly job, or the interval that contains now
for any other job (aligned to the UNIX epoch, so every worker computes the
same period). All in UTC.
"""

from datetime import UTC, datetime

from typed_time_provider import Microseconds

from app.contracts.jobs import PeriodicRunDecision
from app.schemas.constants.jobs import PeriodicJobRunStatus
from app.schemas.domain.jobs import PeriodicJobRunDocument
from app.schemas.dto.job_queue import PeriodicRunStart
from app.schemas.typings.platform.constrained_integers import (
    JobAttemptCount,
    JobIntervalSeconds,
)
from app.schemas.typings.platform.constrained_strings import JobPeriodKey

MICROSECONDS_PER_SECOND: int = 1_000_000
DAY_SECONDS: int = 24 * 60 * 60
WEEK_SECONDS: int = 7 * DAY_SECONDS
INTERVAL_START_FORMAT: str = "%Y-%m-%dT%H:%M:%SZ"
# A weekly job failing all week is retried thousands of times; the count
# stops at the largest JobAttemptCount.
MAX_RECORDED_ATTEMPTS: int = 1000


def compute_period_key(
    interval_seconds: JobIntervalSeconds,
    now: Microseconds,
) -> JobPeriodKey:
    """
    The period of `now` for a job that runs every `interval_seconds`:
    "2026-10-02" (daily), "2026-W40" (weekly) or "2026-10-02T14:15:00Z"
    (the start of the interval otherwise).
    """

    seconds: int = int(now) // MICROSECONDS_PER_SECOND
    moment: datetime = datetime.fromtimestamp(seconds, tz=UTC)
    interval: int = int(interval_seconds)
    if interval == DAY_SECONDS:
        return JobPeriodKey(moment.date().isoformat())

    if interval == WEEK_SECONDS:
        iso_year, iso_week, _ = moment.isocalendar()
        return JobPeriodKey(f"{iso_year:04d}-W{iso_week:02d}")

    interval_start: datetime = datetime.fromtimestamp(
        seconds - seconds % interval,
        tz=UTC,
    )
    return JobPeriodKey(interval_start.strftime(INTERVAL_START_FORMAT))


def decide_periodic_run_start(start: PeriodicRunStart) -> PeriodicRunDecision:
    """
    The decision of whether this worker starts the job in this period, given
    the stored run of the period:

    - no run yet: start it (RUNNING, first attempt);
    - SUCCEEDED: never again in this period;
    - RUNNING under a live lease: another worker runs it;
    - FAILED before its `retry_at`: wait;
    - a RUNNING run whose lease ended (its worker died) or a FAILED run past
      its `retry_at`: take it over as the next attempt.
    """

    def decide(stored: PeriodicJobRunDocument | None) -> PeriodicJobRunDocument | None:
        if stored is None:
            return PeriodicJobRunDocument(
                job_name=start.job_name,
                period_key=start.period_key,
                started_at=start.now,
                lease_until=start.lease_until,
                lease_token=start.lease_token,
                created_at=start.now,
                updated_at=start.now,
            )

        if not may_take_over(stored, start.now):
            return None

        taken_over: PeriodicJobRunDocument = stored.model_copy(deep=True)
        taken_over.status = PeriodicJobRunStatus.RUNNING
        taken_over.attempts = JobAttemptCount(
            min(int(stored.attempts) + 1, MAX_RECORDED_ATTEMPTS)
        )
        taken_over.started_at = start.now
        taken_over.lease_until = start.lease_until
        taken_over.lease_token = start.lease_token
        taken_over.finished_at = None
        taken_over.retry_at = None
        taken_over.updated_at = start.now
        return taken_over

    return decide


def may_take_over(stored: PeriodicJobRunDocument, now: Microseconds) -> bool:
    """Whether a stored run of the period may be started again now."""

    if stored.status is PeriodicJobRunStatus.SUCCEEDED:
        return False

    if stored.status is PeriodicJobRunStatus.RUNNING:
        return stored.lease_until is None or stored.lease_until < now

    return stored.retry_at is None or stored.retry_at <= now
