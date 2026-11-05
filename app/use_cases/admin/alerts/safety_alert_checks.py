"""
The checks of the platform's own watchers that do not depend on Sentry:

- `missed_job_runs`: periodic jobs whose heartbeat is past its `due_by`
  (the workers write it after each success: the last success plus the
  job's interval and grace). Only heartbeats of this release count: a job
  a deploy removed keeps the old release's stamp and is never missed.
- `payment_mismatch`: the mismatches of the latest daily payment
  reconciliation with Flitt and Stripe (today's, else yesterday's).
"""

from collections.abc import Mapping

from typed_time_provider import Microseconds

from app.contracts.platform_safety import (
    PaymentReconciliationRepoContract,
    PeriodicJobHeartbeatRepoContract,
)
from app.schemas.constants.monitoring import PlatformAlertCode
from app.schemas.domain.payment_reconciliations import PaymentReconciliationDocument
from app.schemas.domain.periodic_job_heartbeats import PeriodicJobHeartbeatDocument
from app.schemas.dto.platform_alerts import AlertObservation, PlatformAlertRule
from app.schemas.typings.platform.constrained_strings import ReleaseVersion
from app.schemas.typings.storage.constrained_integers import DocumentQueryLimit
from app.use_cases.admin.alerts.alert_checks import AlertCheck, observe
from app.use_cases.admin.alerts.alert_texts import describe_duration
from app.use_cases.shared.payment_reconciliation_days import latest_reconciliation

MICROSECONDS_PER_SECOND: int = 1_000_000
MAX_OVERDUE_READ: DocumentQueryLimit = DocumentQueryLimit(100)
MAX_NAMED: int = 10


class PlatformSafetyAlertChecks:
    """The missed-run and payment-mismatch checks, by alert code."""

    def __init__(
        self,
        job_heartbeat_repo: PeriodicJobHeartbeatRepoContract,
        reconciliation_repo: PaymentReconciliationRepoContract,
        release: ReleaseVersion | None,
    ) -> None:
        self._heartbeats: PeriodicJobHeartbeatRepoContract = job_heartbeat_repo
        self._reconciliations: PaymentReconciliationRepoContract = reconciliation_repo
        self._release: ReleaseVersion | None = release

    def checks(self) -> Mapping[PlatformAlertCode, AlertCheck]:
        return {
            PlatformAlertCode.MISSED_JOB_RUNS: self.missed_job_runs,
            PlatformAlertCode.PAYMENT_MISMATCH: self.payment_mismatch,
        }

    def missed_job_runs(
        self, rule: PlatformAlertRule, now: Microseconds
    ) -> AlertObservation:
        overdue: list[PeriodicJobHeartbeatDocument] = [
            heartbeat
            for heartbeat in self._heartbeats.list_overdue(now, MAX_OVERDUE_READ)
            if heartbeat.release == self._release
        ]
        if not overdue:
            return observe(rule, 0, "Every periodic job succeeded within its interval.")

        named: str = "; ".join(
            describe_overdue(heartbeat, now) for heartbeat in overdue[:MAX_NAMED]
        )
        more: str = (
            f" and {len(overdue) - MAX_NAMED} more" if len(overdue) > MAX_NAMED else ""
        )
        return observe(
            rule,
            len(overdue),
            f"Missed periodic jobs: {named}{more}. Check the workers of their "
            "lanes and the jobs' errors.",
        )

    def payment_mismatch(
        self, rule: PlatformAlertRule, now: Microseconds
    ) -> AlertObservation:
        latest: PaymentReconciliationDocument | None = latest_reconciliation(
            self._reconciliations, now
        )
        if latest is None:
            return observe(rule, 0, "No payment reconciliation ran today or yesterday.")

        count: int = len(latest.mismatches)
        detail: str = (
            f"The reconciliation of {latest.day} compared "
            f"{int(latest.checked_count)} payments with Flitt and Stripe "
            f"({int(latest.unreadable_count)} could not be read): "
            + (
                f"{count} differ from the platform's record. See the admin system page."
                if count
                else "all match."
            )
        )
        return observe(rule, count, detail)


def describe_overdue(heartbeat: PeriodicJobHeartbeatDocument, now: Microseconds) -> str:
    """ "end_trials (every 1 h, lane default): last success 3 h 5 min ago"."""

    every: str = describe_duration(int(heartbeat.interval_seconds))
    head: str = f"{heartbeat.job_name} (every {every}, lane {heartbeat.lane.value})"
    if heartbeat.last_succeeded_at is None:
        since: int = seconds_between(heartbeat.registered_at, now)
        return (
            f"{head}: no success since it was registered {describe_duration(since)} ago"
        )

    ago: int = seconds_between(heartbeat.last_succeeded_at, now)
    return f"{head}: last success {describe_duration(ago)} ago"


def seconds_between(earlier: Microseconds, later: Microseconds) -> int:
    return max(0, (int(later) - int(earlier)) // MICROSECONDS_PER_SECOND)
