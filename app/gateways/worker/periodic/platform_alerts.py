"""
The platform alerts (`CheckPlatformAlertsUseCase`, docs/operations/slo.md)
as a periodic job of the background worker: every five minutes one worker
reads the persisted runs and counters, and an alert that starts, still
fires after its cooldown or resolves goes to the platform team through
the queue (`send_platform_alert`).

The job cannot report its own absence: when no worker runs at all, the
Sentry cron monitor of this job (SENTRY_DSN) and the external uptime check
of GET /readyz page instead (docs/operations/runbooks/stuck-worker.md).
"""

from app.contracts.jobs import PeriodicJobOperator
from app.gateways.worker.background_worker import PeriodicJobSpec
from app.schemas.typings.platform.constrained_integers import JobIntervalSeconds
from app.schemas.typings.platform.constrained_strings import JobName

PLATFORM_ALERTS_JOB: JobName = JobName("platform_alerts")
PLATFORM_ALERTS_INTERVAL: JobIntervalSeconds = JobIntervalSeconds(5 * 60)


def platform_alerts_job(operator: PeriodicJobOperator) -> PeriodicJobSpec:
    """The periodic job spec that runs `operator` every five minutes."""

    return PeriodicJobSpec(
        name=PLATFORM_ALERTS_JOB,
        interval_seconds=PLATFORM_ALERTS_INTERVAL,
        operator=operator,
    )
