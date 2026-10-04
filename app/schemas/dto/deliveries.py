"""
The inbox and the outbox: what webhooks store for the worker, what the
worker hands between the steps of processing a message and of sending one.
"""

from base_pydantic_schemas import ImmutableDTO
from typed_time_provider import Microseconds

from app.schemas.constants.channels import ChannelKind
from app.schemas.constants.deliveries import DeliveryFailureKind, DeliveryFailureReason
from app.schemas.domain.businesses import ManagerContact
from app.schemas.domain.channels import ChannelDocument
from app.schemas.domain.inbound_events import InboundEventDocument
from app.schemas.domain.outbound_messages import (
    OutboundBillingDocuments,
    OutboundMessageDocument,
    OutboundTemplate,
)
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
from app.schemas.typings.notifications.constrained_strings import StaffAlertSubject
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
    platform events). `is_final_attempt`: the job's last try, when what
    cannot be read is given up instead of tried again.
    """

    event: InboundEventDocument
    message: InboundMessage | None = None
    is_final_attempt: IsFinalJobAttempt = False


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
    the handoff to NOTIFIED or NOTIFICATION_FAILED. `deliver_after` holds it
    until the contact's quiet hours end. `template` is the WhatsApp template
    it goes out as instead of the staff notification template (an owner's
    report, with its own body parameters).
    """

    business_id: BusinessId
    contact: ManagerContact
    text: MessageText
    handoff_id: HandoffId | None = None
    # Another subject the notification is queued once per contact for.
    subject: StaffAlertSubject | None = None
    deliver_after: Microseconds | None = None
    template: OutboundTemplate | None = None
    # PDFs of an invoice attached to an e-mail to the billing contact.
    billing_documents: OutboundBillingDocuments | None = None


class OutboundAttempt(ImmutableDTO):
    """
    One send attempt of an outbox message: the parts delivered so far (all
    of them when `failure` is None) and why it stopped otherwise (`failure`
    decides the retry, `reason` says it to the owner).
    `channel` is the business channel a reply was sent with (its health
    follows the outcome only while it still has that connection).
    """

    message: OutboundMessageDocument
    channel: ChannelDocument | None = None
    delivered_parts: DeliveredMessageCount
    provider_message_id: ProviderMessageId | None = None
    failure: DeliveryFailureKind | None = None
    reason: DeliveryFailureReason | None = None
    error: DeliveryErrorText | None = None
    retry_after_seconds: RetryAfterSeconds | None = None
    attempted_at: Microseconds
