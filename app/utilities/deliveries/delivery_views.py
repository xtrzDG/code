"""The delivery state of an outbox message, as the cabinet shows it."""

from app.schemas.constants.deliveries import (
    OutboundDeliveryState,
    OutboundMessageStatus,
)
from app.schemas.domain.outbound_messages import OutboundMessageDocument
from app.schemas.dto.conversation_feed.message_deliveries import MessageDeliveryView


def delivery_state_of(message: OutboundMessageDocument) -> OutboundDeliveryState:
    """
    DELIVERED and FAILED (given up) are final; a waiting message is SENDING
    until its first attempt failed, then RETRYING.
    """

    if message.status is OutboundMessageStatus.DELIVERED:
        return OutboundDeliveryState.DELIVERED

    if message.status is OutboundMessageStatus.DEAD:
        return OutboundDeliveryState.FAILED

    if int(message.attempts) == 0:
        return OutboundDeliveryState.SENDING

    return OutboundDeliveryState.RETRYING


def build_delivery_view(message: OutboundMessageDocument) -> MessageDeliveryView:
    state: OutboundDeliveryState = delivery_state_of(message)
    return MessageDeliveryView(
        state=state,
        failure_reason=(
            None
            if state is OutboundDeliveryState.DELIVERED
            else message.last_failure_reason
        ),
        attempts=message.attempts,
        next_attempt_at=(
            message.next_attempt_at if state is OutboundDeliveryState.RETRYING else None
        ),
        delivered_at=message.delivered_at,
    )
