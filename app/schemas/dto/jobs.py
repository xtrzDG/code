from base_pydantic_schemas import ImmutableDTO
from typed_time_provider import Microseconds

from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.platform.booleans import IsFinalJobAttempt
from app.schemas.typings.platform.constrained_integers import ProcessedItemCount
from app.schemas.typings.platform.constrained_strings import JobName
from app.schemas.typings.platform.prefixed_id import QueuedJobId
from app.schemas.typings.platform.strings import JobPayloadJson


class JobTick(ImmutableDTO):
    """Trigger of a periodic job run."""

    job_name: JobName
    scheduled_at: Microseconds


class QueuedJobInput(ImmutableDTO):
    """
    Input of a queued job handler. `is_final_attempt` is True when a failure
    will not be retried, so the handler can leave its work recoverable.
    """

    job_id: QueuedJobId
    job_name: JobName
    payload: JobPayloadJson
    business_id: BusinessId | None = None
    is_final_attempt: IsFinalJobAttempt = False


class JobReport(ImmutableDTO):
    """What one job run did."""

    processed_count: ProcessedItemCount = ProcessedItemCount(0)
