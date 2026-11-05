"""An outbox message whose moment passed is given up, not sent late."""

from typed_time_provider import Microseconds

from app.schemas.constants.deliveries import DeliveryFailureKind, DeliveryFailureReason
from app.schemas.domain.outbound_messages import OutboundMessageDocument
from app.schemas.dto.deliveries import OutboundAttempt
from app.schemas.typings.deliveries.strings import DeliveryErrorText

EXPIRED_ERROR: DeliveryErrorText = DeliveryErrorText(
    "Not sent: its moment passed before it could go out."
)


def expired_attempt(
    message: OutboundMessageDocument,
    now: Microseconds,
) -> OutboundAttempt:
    """An attempt that sends nothing and cannot succeed later."""

    return OutboundAttempt(
        message=message,
        delivered_parts=message.delivered_parts,
        provider_message_id=message.provider_message_id,
        failure=DeliveryFailureKind.REJECTED,
        reason=DeliveryFailureReason.EXPIRED,
        error=EXPIRED_ERROR,
        attempted_at=now,
    )
