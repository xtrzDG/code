"""
A running job handed back by a worker that stops (a deploy, a restart):
due again at once for the next worker, without counting the cut-off
attempt or a lost lease, because it did not fail and its process did not
die with it.
"""

from typed_time_provider import Microseconds

from app.schemas.constants.jobs import QueuedJobStatus
from app.schemas.domain.jobs import QueuedJobDocument
from app.schemas.typings.platform.constrained_integers import JobAttemptCount
from app.schemas.typings.platform.constrained_strings import JobLeaseToken


def hand_back_job(
    current: QueuedJobDocument,
    lease_token: JobLeaseToken,
    now: Microseconds,
) -> QueuedJobDocument | None:
    """
    The job PENDING and due `now`, its cut-off attempt not counted; None
    when it no longer runs under this claim's token (settled, or taken over).
    """

    if current.status is not QueuedJobStatus.RUNNING:
        return None

    if current.lease_token != lease_token:
        return None

    current.status = QueuedJobStatus.PENDING
    current.attempts = JobAttemptCount(max(0, int(current.attempts) - 1))
    current.run_at = now
    current.lease_until = None
    current.lease_token = None
    current.updated_at = now
    return current
