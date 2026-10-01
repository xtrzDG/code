from base_pydantic_schemas import BaseDocument
from pydantic import Field
from typed_time_provider import Microseconds

from app.schemas.constants.jobs import QueuedJobStatus
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.platform.constrained_integers import JobAttemptCount
from app.schemas.typings.platform.constrained_strings import JobName
from app.schemas.typings.platform.prefixed_id import QueuedJobId
from app.schemas.typings.platform.strings import JobErrorText, JobPayloadJson


class QueuedJobDocument(BaseDocument):
    """
    One unit of background work (concept: queue in Postgres for reminders,
    assembly, autotests and retries). Retried with exponential backoff until
    it succeeds or runs out of attempts.
    """

    id: QueuedJobId = Field(default_factory=QueuedJobId)
    name: JobName
    payload: JobPayloadJson
    business_id: BusinessId | None = None
    run_at: Microseconds
    attempts: JobAttemptCount = JobAttemptCount(0)
    status: QueuedJobStatus = QueuedJobStatus.PENDING
    last_error: JobErrorText | None = None
