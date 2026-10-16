"""The worker's request to read the attachments of one customer message."""

from base_pydantic_schemas import ImmutableDTO

from app.schemas.domain.inbound_events import InboundEventDocument
from app.schemas.dto.conversations import InboundMessage
from app.schemas.typings.platform.booleans import IsFinalJobAttempt


class InboundMediaRequest(ImmutableDTO):
    """
    The attachments of one claimed inbox event to read: files downloaded
    and stored, voice notes transcribed. On the job's last attempt a file
    the platform does not hand out (or a transcription service that keeps
    failing) is given up, and the customer is asked to write, instead of
    failing the job.
    """

    event: InboundEventDocument
    message: InboundMessage
    is_final_attempt: IsFinalJobAttempt = False
