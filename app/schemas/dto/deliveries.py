"""
The inbox and the outbox: what webhooks store for the worker, what the
worker hands between the steps of processing a message and of sending one.
"""

from base_pydantic_schemas import ImmutableDTO
from typed_time_provider import Microseconds

from app.schemas.constants.channels import ChannelKind
from app.schemas.constants.deliveries import DeliveryFailureKind
from app.schemas.domain.businesses import ManagerContact
from app.schemas.domain.inbound_events import InboundEventDocument
from app.schemas.domain.outbound_messages import OutboundMessageDocument
from app.schemas.dto.channels.channel_webhooks import ChannelInboundMessage
from app.schemas.dto.conversations import InboundMessage
from app.schemas.dto.voice_webhooks import FinishedCallReport
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.channels.constrained_integers import (
    DeliveredMessageCount,
    WebhookMessageCount,
)
from app.schemas.typings.channels.prefixed_id import ChannelId
from app.schemas.typings.channels.strings import ProviderMessageId
from app.schemas.typings.conversations.booleans import IsConversationHandedOff
from app.schemas.typings.conversations.prefixed_id import ConversationId
from app.schemas.typings.conversations.strings import MessageText
from app.schemas.typings.deliveries.prefixed_id import InboundEventId, OutboundMessageId
from app.schemas.typings.deliveries.strings import DeliveryErrorText, InboundErrorText
from app.schemas.typings.handoffs.prefixed_id import HandoffId
from app.schemas.typings.platform.booleans import IsFinalJobAttempt
from app.schemas.typings.platform.constrained_integers import RetryAfterSeconds

# --- The inbox ---------------------------------------------------------------


class RoutedInboundMessage(ImmutableDTO):
    """A verified customer message and the connected channel it belongs to."""

    business_id: BusinessId
    channel_id: ChannelId
    channel: ChannelKind
    message: ChannelInboundMessage


class InboxIntake(ImmutableDTO):
    """How the messages of one webhook went into the inbox."""

    received: WebhookMessageCount = WebhookMessageCount(0)
    queued: WebhookMessageCount = WebhookMessageCount(0)
    duplicates: WebhookMessageCount = WebhookMessageCount(0)


class VerifiedPostCallReport(ImmutableDTO):
    """A post-call webhook whose signature was checked, and its report."""

    body: bytes
    report: FinishedCallReport


class InboundEventJobPayload(ImmutableDTO):
    """Payload of the jobs that process one inbox event."""

    event_id: InboundEventId


class InboundEventClaim(ImmutableDTO):
    """
    An inbox event this worker (or widget request) now holds until its
    lease ends, with the customer message as the engine reads it (None for
    platform events).
    """

    event: InboundEventDocument
    message: InboundMessage | None = None


class InboundAnswer(ImmutableDTO):
    """
    What the assistant made of a customer message: the reply to send (None
    when staff own the conversation) in its conversation.
    """

    event: InboundEventDocument
    conversation_id: ConversationId | None = None
    text: MessageText | None = None
    is_handed_off: IsConversationHandedOff = False


class InboundFailure(ImmutableDTO):
    """
    Processing of an event failed. A final failure marks it FAILED; another
    one only releases it, so the job's retry may take it at once.
    """

    event_id: InboundEventId
    business_id: BusinessId | None = None
    error: InboundErrorText
    is_final: IsFinalJobAttempt = False


# --- The outbox --------------------------------------------------------------


class OutboundMessageJobPayload(ImmutableDTO):
    """Payload of the job that sends one outbox message."""

    outbound_message_id: OutboundMessageId


class StaffNotification(ImmutableDTO):
    """
    A message to one staff contact of a business. A notification about a
    handoff is queued once per handoff and contact, and its delivery moves
    the handoff to NOTIFIED or NOTIFICATION_FAILED.
    """

    business_id: BusinessId
    contact: ManagerContact
    text: MessageText
    handoff_id: HandoffId | None = None


class OutboundAttempt(ImmutableDTO):
    """
    One send attempt of an outbox message: the parts delivered so far (all
    of them when `failure` is None) and why it stopped otherwise.
    """

    message: OutboundMessageDocument
    delivered_parts: DeliveredMessageCount
    provider_message_id: ProviderMessageId | None = None
    failure: DeliveryFailureKind | None = None
    error: DeliveryErrorText | None = None
    retry_after_seconds: RetryAfterSeconds | None = None
    attempted_at: Microseconds
