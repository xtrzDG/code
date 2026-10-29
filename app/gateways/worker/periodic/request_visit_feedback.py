"""
The requests for feedback after visits as a periodic job of the background
worker (`RequestVisitFeedbackUseCase`), every ten minutes: a customer is
asked within ten minutes of the delay the owner chose. Registered with one
line in the worker's list of periodic jobs.
"""

from app.contracts.jobs import PeriodicJobOperator
from app.gateways.worker.background_worker import PeriodicJobSpec
from app.schemas.typings.platform.constrained_integers import JobIntervalSeconds
from app.schemas.typings.platform.constrained_strings import JobName

REQUEST_VISIT_FEEDBACK_JOB: JobName = JobName("request_visit_feedback")
REQUEST_VISIT_FEEDBACK_INTERVAL: JobIntervalSeconds = JobIntervalSeconds(10 * 60)


def request_visit_feedback_job(operator: PeriodicJobOperator) -> PeriodicJobSpec:
    """The periodic job spec that runs `operator` every ten minutes."""

    return PeriodicJobSpec(
        name=REQUEST_VISIT_FEEDBACK_JOB,
        interval_seconds=REQUEST_VISIT_FEEDBACK_INTERVAL,
        operator=operator,
    )
