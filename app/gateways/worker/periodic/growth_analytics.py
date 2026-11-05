"""
The growth analytics' daily jobs of the background worker: the purge of
Web Vital samples older than 90 days (`PurgeWebVitalsUseCase`) and the
reconciliation of product events with the stored records
(`ReconcileProductEventsUseCase`), each once a day across workers.
"""

from app.contracts.jobs import PeriodicJobOperator
from app.gateways.worker.background_worker import PeriodicJobSpec
from app.schemas.typings.platform.constrained_integers import JobIntervalSeconds
from app.schemas.typings.platform.constrained_strings import JobName

PURGE_WEB_VITALS_JOB: JobName = JobName("purge_web_vitals")
RECONCILE_PRODUCT_EVENTS_JOB: JobName = JobName("reconcile_product_events")
GROWTH_ANALYTICS_INTERVAL: JobIntervalSeconds = JobIntervalSeconds(24 * 60 * 60)


def purge_web_vitals_job(operator: PeriodicJobOperator) -> PeriodicJobSpec:
    """The periodic job spec that runs the Web Vitals purge once a day."""

    return PeriodicJobSpec(
        name=PURGE_WEB_VITALS_JOB,
        interval_seconds=GROWTH_ANALYTICS_INTERVAL,
        operator=operator,
    )


def reconcile_product_events_job(operator: PeriodicJobOperator) -> PeriodicJobSpec:
    """The periodic job spec that reconciles the product events once a day."""

    return PeriodicJobSpec(
        name=RECONCILE_PRODUCT_EVENTS_JOB,
        interval_seconds=GROWTH_ANALYTICS_INTERVAL,
        operator=operator,
    )
