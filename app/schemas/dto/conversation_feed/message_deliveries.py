"""How a message written in the cabinet travels to the customer."""

from base_pydantic_schemas import ImmutableDTO
from typed_time_provider import Microseconds

from app.schemas.constants.deliveries import (
    DeliveryFailureReason,
    OutboundDeliveryState,
)
from app.schemas.typings.deliveries.constrained_integers import DeliveryAttemptCount


class MessageDeliveryView(ImmutableDTO):
    """
    The delivery of a staff reply, read from its outbox message: where it
    stands (`state`), why the last attempt failed (`failure_reason`, while
    it is tried again and after it was given up), the attempts so far, when
    the next one is due and when the customer's platform accepted it.
    """

    state: OutboundDeliveryState
    failure_reason: DeliveryFailureReason | None = None
    attempts: DeliveryAttemptCount
    next_attempt_at: Microseconds | None = None
    delivered_at: Microseconds | None = None
