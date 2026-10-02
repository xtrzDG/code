from base_pydantic_schemas import BaseDocument, PersistentDocument
from pydantic import Field
from typed_time_provider import Microseconds

from app.schemas.constants.channels import ChannelKind
from app.schemas.constants.deliveries import OutboundMessageKind, OutboundMessageStatus
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
    """

    id: OutboundMessageId
    business_id: BusinessId
    kind: OutboundMessageKind
    idempotency_key: OutboundIdempotencyKey
    recipient_key: OutboundRecipientKey
    customer: CustomerRecipient | None = None
    staff_contact: ManagerContact | None = None
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
