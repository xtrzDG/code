"""
The platform admin's client list, computed ahead, as a periodic job of the
background worker (`RefreshClientStandingsUseCase`), every 15 minutes: the
list then reads one keyset page and database counts instead of
summarizing every client on each request. Registered with one line in the
worker's list of periodic jobs.
"""

from app.contracts.jobs import PeriodicJobOperator
from app.gateways.worker.background_worker import PeriodicJobSpec
from app.schemas.typings.platform.constrained_integers import JobIntervalSeconds
from app.schemas.typings.platform.constrained_strings import JobName

REFRESH_CLIENT_STANDINGS_JOB: JobName = JobName("refresh_client_standings")
REFRESH_CLIENT_STANDINGS_INTERVAL: JobIntervalSeconds = JobIntervalSeconds(15 * 60)


def refresh_client_standings_job(operator: PeriodicJobOperator) -> PeriodicJobSpec:
    """The periodic job spec that runs `operator` every 15 minutes."""

    return PeriodicJobSpec(
        name=REFRESH_CLIENT_STANDINGS_JOB,
        interval_seconds=REFRESH_CLIENT_STANDINGS_INTERVAL,
        operator=operator,
    )
