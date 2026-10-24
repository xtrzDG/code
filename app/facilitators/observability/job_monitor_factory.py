"""Choose the job monitor for the container wiring."""

from app.contracts.observability import JobMonitorFacilitatorContract
from app.facilitators.observability.null_job_monitor_facilitator import (
    NullJobMonitorFacilitator,
)
from app.facilitators.observability.sentry_error_reporting_facilitator import (
    SentryErrorReportingFacilitator,
)
from app.facilitators.observability.sentry_job_monitor_facilitator import (
    SentryJobMonitorFacilitator,
)


def build_job_monitor_facilitator(
    error_reporter: SentryErrorReportingFacilitator,
) -> JobMonitorFacilitatorContract:
    """Sentry Crons check-ins once the reporter set Sentry up, else nothing."""

    if error_reporter.is_enabled:
        return SentryJobMonitorFacilitator()

    return NullJobMonitorFacilitator()
