"""
Due queued jobs run in the calling thread, lane after lane: the tick of
`BackgroundWorker.run_once` and `run_queued_jobs` (tests and one-off runs;
a running worker's lanes have their own threads, `LaneThreads`).
"""

from collections.abc import Mapping, Sequence

from app.gateways.worker.job_failure_reporter import JobFailureReporter
from app.gateways.worker.queued_job_runner import QueuedJobOutcome, QueuedJobRunner
from app.schemas.constants.jobs import JobLane
from app.schemas.typings.platform.constrained_integers import (
    JobClaimLimit,
    WorkerLaneConcurrency,
)
from app.schemas.typings.platform.constrained_strings import JobName

# Claims at most this many rounds per lane, so a clock that keeps moving
# cannot keep a tick busy forever.
MAX_CLAIM_ROUNDS_PER_TICK: int = 100
JOB_QUEUE_JOB: JobName = JobName("job_queue")


def run_due_queued_jobs(
    runner: QueuedJobRunner,
    lanes: Sequence[JobLane],
    lane_concurrency: Mapping[JobLane, WorkerLaneConcurrency],
    failure_reporter: JobFailureReporter,
) -> tuple[int, int]:
    """
    Every due job of these lanes, claimed a lane's concurrency at a time
    (jobs they queue for now too): (jobs run, failures). A queue that cannot
    be reached is reported and ends that lane's rounds.
    """

    runs: int = 0
    failures: int = 0
    for lane in lanes:
        limit = JobClaimLimit(int(lane_concurrency.get(lane, 1)))
        for _ in range(MAX_CLAIM_ROUNDS_PER_TICK):
            try:
                jobs, lease_token = runner.claim(lane, limit)
            except Exception as error:  # noqa: BLE001 - queue unreachable
                failure_reporter.report(JOB_QUEUE_JOB, error)
                failures += 1
                break

            if not jobs:
                break

            for job in jobs:
                outcome: QueuedJobOutcome = runner.run(job, lease_token)
                runs += int(outcome.has_run)
                failures += int(outcome.has_failed)

    return runs, failures
