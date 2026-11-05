from base_pydantic_schemas import BaseDocument
from typed_time_provider import Microseconds

from app.schemas.constants.jobs import JobLane
from app.schemas.typings.platform.constrained_integers import JobIntervalSeconds
from app.schemas.typings.platform.constrained_strings import JobName, ReleaseVersion


class PeriodicJobHeartbeatDocument(BaseDocument):
    """
    The heartbeat of one shared periodic job (a platform collection stored
    under the job's name, migration 1230), written by the workers and read
    by the `missed_job_runs` alert, so a job that stopped running pages
    the team without Sentry Crons.

    Every worker registers each job it knows when it starts (`release`
    then names its build; `registered_at` the first registration) and
    writes `last_succeeded_at` after a run of the job succeeded.
    `due_by` is when the next success is due at the latest: the last
    success (else the registration) plus the job's interval and its grace
    (`job_run_allowance`); a heartbeat past it is a missed run.
    """

    job_name: JobName
    interval_seconds: JobIntervalSeconds
    lane: JobLane
    release: ReleaseVersion | None = None
    registered_at: Microseconds
    last_succeeded_at: Microseconds | None = None
    due_by: Microseconds
