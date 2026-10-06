"""
The post-deploy data tasks as a periodic job of the batch worker
(`RunDataTasksUseCase`), every 5 minutes: once the release overlap is
over, documents of older shapes are rewritten and lookup columns of older
rows filled, in keyset batches, without an operator
(docs/operations/deploys.md). Registered with one line in the worker's
list of periodic jobs.
"""

from app.contracts.jobs import PeriodicJobOperator
from app.gateways.worker.background_worker import PeriodicJobSpec
from app.schemas.constants.jobs import JobLane
from app.schemas.typings.platform.constrained_integers import JobIntervalSeconds
from app.schemas.typings.platform.constrained_strings import JobName

RUN_DATA_TASKS_JOB: JobName = JobName("run_data_tasks")
RUN_DATA_TASKS_INTERVAL: JobIntervalSeconds = JobIntervalSeconds(5 * 60)


def run_data_tasks_job(operator: PeriodicJobOperator) -> PeriodicJobSpec:
    """
    The periodic job spec that runs `operator` every 5 minutes on the batch
    worker (the `default` lane), never on the workers that answer customers.
    """

    return PeriodicJobSpec(
        name=RUN_DATA_TASKS_JOB,
        interval_seconds=RUN_DATA_TASKS_INTERVAL,
        operator=operator,
        lane=JobLane.DEFAULT,
    )
