"""
What /metrics calls an outbox message's provider and attempt outcome:
the customer's channel, the staff contact's channel or web push, never
an address or id.
"""

from app.schemas.constants.deliveries import OutboundMessageStatus
from app.schemas.constants.telemetry import OutboundAttemptOutcome
from app.schemas.domain.outbound_messages import OutboundMessageDocument
from app.schemas.typings.observability.constrained_strings import MetricsLabel

WEB_PUSH_PROVIDER: MetricsLabel = MetricsLabel("web_push")
UNKNOWN_PROVIDER: MetricsLabel = MetricsLabel("unknown")


def outbound_provider_label(message: OutboundMessageDocument) -> MetricsLabel:
    if message.customer is not None:
        return MetricsLabel(message.customer.channel.value)

    if message.staff_contact is not None:
        return MetricsLabel(message.staff_contact.channel.value)

    return WEB_PUSH_PROVIDER if message.push is not None else UNKNOWN_PROVIDER


def outbound_attempt_outcome(
    message: OutboundMessageDocument,
) -> OutboundAttemptOutcome:
    """What a recorded attempt left: delivered, a retry later, or dead."""

    if message.status is OutboundMessageStatus.DELIVERED:
        return OutboundAttemptOutcome.DELIVERED

    if message.status is OutboundMessageStatus.DEAD:
        return OutboundAttemptOutcome.DEAD

    return OutboundAttemptOutcome.RETRY
