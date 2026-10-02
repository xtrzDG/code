from base_pydantic_schemas import BaseDocument, PersistentDocument, SchemaVersion
from pydantic import Field
from typed_time_provider import Microseconds

from app.schemas.constants.channels import ChannelKind
from app.schemas.constants.deliveries import OutboundMessageKind, OutboundMessageStatus
from app.schemas.constants.notifications import WebPushUrgency
from app.schemas.domain.businesses import ManagerContact
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.channels.constrained_integers import DeliveredMessageCount
from app.schemas.typings.channels.constrained_strings import (
    WhatsAppTemplateLanguageCode,
    WhatsAppTemplateName,
)
from app.schemas.typings.channels.prefixed_id import ChannelId
from app.schemas.typings.channels.strings import ProviderMessageId
from app.schemas.typings.conversations.prefixed_id import ConversationId, MessageId
from app.schemas.typings.conversations.strings import ChannelUserId, MessageText
from app.schemas.typings.deliveries.constrained_integers import DeliveryAttemptCount
from app.schemas.typings.deliveries.constrained_strings import (
    OutboundIdempotencyKey,
    OutboundRecipientKey,
)
from app.schemas.typings.deliveries.prefixed_id import OutboundMessageId
from app.schemas.typings.deliveries.strings import DeliveryErrorText
from app.schemas.typings.handoffs.prefixed_id import HandoffId
from app.schemas.typings.notifications.constrained_strings import (
    CabinetDeepLink,
    PushNotificationTag,
)
from app.schemas.typings.notifications.prefixed_id import PushSubscriptionId
from app.schemas.typings.notifications.strings import StaffAlertTitle
from app.schemas.typings.users.prefixed_id import UserId


class CustomerRecipient(PersistentDocument):
    """
    A customer in the business's channel. The credential is read from the
    channel at send time (never stored here), so a reconnected bot is used.
    """

    channel_id: ChannelId
    channel: ChannelKind
    channel_user_id: ChannelUserId


class OutboundTemplate(PersistentDocument):
    """A Meta-approved WhatsApp template; the message text is its parameter."""

    name: WhatsAppTemplateName
    language_code: WhatsAppTemplateLanguageCode


class PushRecipient(PersistentDocument):
    """
    A cabinet user's device (Web Push subscription) and what its
    notification shows besides the text: the title, the page it opens, the
    tag a newer notification about the same thing replaces it by, and how
    soon the device should wake. The subscription's keys are read at send
    time (never copied here).
    """

    subscription_id: PushSubscriptionId
    user_id: UserId
    title: StaffAlertTitle
    url: CabinetDeepLink | None = None
    tag: PushNotificationTag | None = None
    urgency: WebPushUrgency = WebPushUrgency.NORMAL


class OutboundMessageDocument(BaseDocument):
    """
    One message to send (the outbox): an assistant reply to a customer or a
    notification to staff. Queued once per idempotency key (the id derives
    from it), sent by the worker, retried with backoff until it is
    DELIVERED or DEAD, so its delivery state can be looked up.

    Long texts go out in several platform messages; `delivered_parts`
    counts those already sent, so a retry continues after them instead of
    repeating them. `recipient_key` names who it goes to: messages of one
    recipient go out in the order they were queued.

    Version 2: a staff notification may go to a cabinet user's device
    (`push`) instead of a staff contact.
    """

    schema_version: SchemaVersion = SchemaVersion("2")
    id: OutboundMessageId
    business_id: BusinessId
    kind: OutboundMessageKind
    idempotency_key: OutboundIdempotencyKey
    recipient_key: OutboundRecipientKey
    customer: CustomerRecipient | None = None
    staff_contact: ManagerContact | None = None
    push: PushRecipient | None = None
    text: MessageText = Field(repr=False)
    template: OutboundTemplate | None = None
    conversation_id: ConversationId | None = None
    source_message_id: MessageId | None = None
    handoff_id: HandoffId | None = None
    status: OutboundMessageStatus = OutboundMessageStatus.PENDING
    attempts: DeliveryAttemptCount = DeliveryAttemptCount(0)
    delivered_parts: DeliveredMessageCount = DeliveredMessageCount(0)
    next_attempt_at: Microseconds | None = None
    last_error: DeliveryErrorText | None = None
    provider_message_id: ProviderMessageId | None = None
    delivered_at: Microseconds | None = None
