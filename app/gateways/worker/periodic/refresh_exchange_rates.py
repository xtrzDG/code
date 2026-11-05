"""
The refresh of the dated exchange rates as a periodic job of the background
worker (`RefreshExchangeRatesUseCase`), every six hours: the NBG sets the
lari's rates once a working day (valid from the next day) and the ECB its
reference rates around 16:00 CET, so each day's rates are stored within
hours, and a run that finds nothing new rewrites the same day's rows.
"""

from app.contracts.jobs import PeriodicJobOperator
from app.gateways.worker.background_worker import PeriodicJobSpec
from app.schemas.typings.platform.constrained_integers import JobIntervalSeconds
from app.schemas.typings.platform.constrained_strings import JobName

REFRESH_EXCHANGE_RATES_JOB: JobName = JobName("refresh_exchange_rates")
REFRESH_EXCHANGE_RATES_INTERVAL: JobIntervalSeconds = JobIntervalSeconds(6 * 60 * 60)


def refresh_exchange_rates_job(operator: PeriodicJobOperator) -> PeriodicJobSpec:
    """The periodic job spec that runs `operator` every six hours."""

    return PeriodicJobSpec(
        name=REFRESH_EXCHANGE_RATES_JOB,
        interval_seconds=REFRESH_EXCHANGE_RATES_INTERVAL,
        operator=operator,
    )
