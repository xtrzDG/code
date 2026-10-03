"""
Identities of the inbox and the outbox: event and message ids derived from
what makes them unique, recipient keys and the serial keys of their jobs.
"""

import hashlib
from uuid import UUID, uuid4, uuid5

from app.schemas.constants.channels import ChannelKind
from app.schemas.domain.businesses import ManagerContact
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.channels.prefixed_id import ChannelId
from app.schemas.typings.channels.strings import ProviderMessageId
from app.schemas.typings.conversations.prefixed_id import ConversationId, MessageId
from app.schemas.typings.conversations.strings import ChannelUserId
from app.schemas.typings.deliveries.constrained_strings import (
    OutboundIdempotencyKey,
    OutboundRecipientKey,
)
from app.schemas.typings.deliveries.prefixed_id import InboundEventId, OutboundMessageId
from app.schemas.typings.handoffs.prefixed_id import HandoffId
from app.schemas.typings.notifications.constrained_strings import StaffAlertSubject
from app.schemas.typings.platform.constrained_strings import JobSerialKey

# Fixed namespaces of the derived ids (never change them: stored ids and
# the dedup of redelivered webhooks depend on them).
INBOUND_EVENT_NAMESPACE: UUID = UUID("6f1b8f52-2c55-4c1e-9a43-3a1f0c9b7e10")
OUTBOUND_MESSAGE_NAMESPACE: UUID = UUID("0c7d3a8e-5b1f-4e62-8d2a-9b4c1e7f3a25")
PLATFORM_SCOPE: str = "platform"
MAX_PROVIDER_MESSAGE_ID_LENGTH: int = 256
# Serial keys carry a digest of who they serialize (addresses and user ids
# may hold characters job keys do not allow, and should not be shown in the
# job list).
SERIAL_KEY_DIGEST_LENGTH: int = 40


def derive_inbound_event_id(
    business_id: BusinessId | None,
    channel: ChannelKind,
    provider_message_id: ProviderMessageId,
) -> InboundEventId:
    """The same message of the same business and channel: the same event."""

    scope: str = PLATFORM_SCOPE if business_id is None else str(business_id)
    name: str = f"{scope}|{channel.value}|{provider_message_id}"
    return InboundEventId(uuid5(INBOUND_EVENT_NAMESPACE, name))


def derive_outbound_message_id(
    business_id: BusinessId,
    idempotency_key: OutboundIdempotencyKey,
) -> OutboundMessageId:
    """The same idempotency key of a business: the same outbox message."""

    return OutboundMessageId(
        uuid5(OUTBOUND_MESSAGE_NAMESPACE, f"{business_id}|{idempotency_key}")
    )


def new_provider_message_id() -> ProviderMessageId:
    """An id for a message the platform gave none (the website widget)."""

    return ProviderMessageId(f"local:{uuid4()}")


def bounded_provider_message_id(
    provider_message_id: ProviderMessageId | None,
) -> ProviderMessageId:
    """
    The platform's id when it named a usable one, else a fresh local one (a
    message without an id cannot be recognised when it comes again).
    """

    if provider_message_id is None:
        return new_provider_message_id()

    text: str = str(provider_message_id).strip()
    if text == "" or len(text) > MAX_PROVIDER_MESSAGE_ID_LENGTH:
        return new_provider_message_id()

    return provider_message_id


def reply_idempotency_key(
    conversation_id: ConversationId | None,
    reply_message_id: MessageId,
) -> OutboundIdempotencyKey:
    """One outbox message per stored assistant reply of a conversation."""

    conversation: str = "none" if conversation_id is None else str(conversation_id)
    return OutboundIdempotencyKey(f"reply:{conversation}:{reply_message_id}")


def staff_idempotency_key(
    contact: ManagerContact,
    handoff_id: HandoffId | None,
    subject: StaffAlertSubject | None = None,
) -> OutboundIdempotencyKey:
    """
    A handoff, or another subject an alert names (a call's summary),
    notifies each contact once; other notifications are new each time they
    are sent.
    """

    return OutboundIdempotencyKey(
        f"staff:{alert_subject(handoff_id, subject)}:{contact.channel.value}:"
        f"{contact.address}"
    )


def alert_subject(
    handoff_id: HandoffId | None,
    subject: StaffAlertSubject | None,
) -> str:
    """What makes alerts the same: their handoff, their subject, else nothing."""

    if handoff_id is not None:
        return f"handoff:{handoff_id}"

    return str(uuid4()) if subject is None else str(subject)


def customer_recipient_key(
    channel_id: ChannelId,
    channel_user_id: ChannelUserId,
) -> OutboundRecipientKey:
    return OutboundRecipientKey(f"customer:{channel_id}:{channel_user_id}")


def staff_recipient_key(contact: ManagerContact) -> OutboundRecipientKey:
    return OutboundRecipientKey(f"staff:{contact.channel.value}:{contact.address}")


def inbound_serial_key(
    business_id: BusinessId | None,
    channel: ChannelKind,
    sender: str,
) -> JobSerialKey:
    """
    Messages of one sender are processed one at a time, oldest first, so
    replies to one customer keep their order.
    """

    scope: str = PLATFORM_SCOPE if business_id is None else str(business_id)
    return JobSerialKey(f"inbound:{digest(f'{scope}|{channel.value}|{sender}')}")


def outbound_serial_key(
    business_id: BusinessId,
    recipient_key: OutboundRecipientKey,
) -> JobSerialKey:
    """Messages to one recipient are sent one at a time, in queue order."""

    return JobSerialKey(f"outbound:{digest(f'{business_id}|{recipient_key}')}")


def digest(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()[:SERIAL_KEY_DIGEST_LENGTH]
