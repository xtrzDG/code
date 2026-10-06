"""
The five-minute read of every linked outside calendar (Google free/busy,
iCal feeds, booking systems) into the resources' busy times
(`SyncDueCalendarsUseCase`). Registered with one line in the worker's list
of periodic jobs; it runs on the default lane (the batch worker), so a slow
feed never holds up a customer's reply; availability reads a stale source
itself.
"""

from app.contracts.jobs import PeriodicJobOperator
from app.gateways.worker.background_worker import PeriodicJobSpec
from app.schemas.constants.jobs import JobLane
from app.schemas.typings.platform.constrained_integers import JobIntervalSeconds
from app.schemas.typings.platform.constrained_strings import JobName
from app.utilities.calendar_sync.busy_windows import SYNC_INTERVAL_SECONDS

SYNC_CALENDARS_JOB: JobName = JobName("sync_calendars")
SYNC_CALENDARS_INTERVAL: JobIntervalSeconds = JobIntervalSeconds(SYNC_INTERVAL_SECONDS)


def sync_calendars_job(operator: PeriodicJobOperator) -> PeriodicJobSpec:
    """The periodic job spec that runs `operator` every five minutes."""

    return PeriodicJobSpec(
        name=SYNC_CALENDARS_JOB,
        interval_seconds=SYNC_CALENDARS_INTERVAL,
        operator=operator,
        lane=JobLane.DEFAULT,
    )
