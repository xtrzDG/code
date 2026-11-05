"""Quick messages of one customer answered together (grouped bursts)."""

from base_pydantic_schemas import ImmutableDTO
from pydantic import Field
from typed_time_provider import Microseconds

from app.schemas.domain.inbound_events import InboundEventDocument
from app.schemas.dto.deliveries import InboundEventClaim


class InboundBurst(ImmutableDTO):
    """
    What a `process_inbound_message` job found: the customer's unprocessed
    messages, oldest first, now held by this worker (`claims`) and answered
    in one turn; or, while the customer may still be writing, none yet and
    `answer_at`, when the job comes back. `trigger` is the job's own event.
    """

    trigger: InboundEventDocument
    claims: list[InboundEventClaim] = Field(default_factory=list[InboundEventClaim])
    answer_at: Microseconds | None = None


class HeldInboundEvents(ImmutableDTO):
    """
    Messages answered by the reply to a later message of the same burst:
    each gets that event's outcome (status, conversation, outbox message).
    """

    events: list[InboundEventDocument]
    answered_by: InboundEventDocument
