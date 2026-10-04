"""Queuing messages to customers in the channels testbed's outbox."""

from uuid import uuid4

from app.schemas.constants.deliveries import OutboundMessageKind
from app.schemas.domain.channels import ChannelDocument
from app.schemas.domain.outbound_messages import (
    CustomerRecipient,
    OutboundMessageDocument,
    OutboundTemplate,
)
from app.schemas.typings.channels.constrained_strings import (
    WhatsAppTemplateLanguageCode,
    WhatsAppTemplateName,
)
from app.schemas.typings.conversations.strings import ChannelUserId, MessageText
from app.schemas.typings.deliveries.constrained_strings import OutboundIdempotencyKey
from app.use_cases.shared.outbox_queue import queue_outbound_message
from app.utilities.deliveries.delivery_keys import (
    customer_recipient_key,
    derive_outbound_message_id,
)
from tests.channels.testbed import ChannelsTestbed


def template(
    name: str, language_code: str, parameters: list[str]
) -> OutboundTemplate:
    return OutboundTemplate(
        name=WhatsAppTemplateName(name),
        language_code=WhatsAppTemplateLanguageCode(language_code),
        body_parameters=[MessageText(value) for value in parameters],
    )


def queue_customer_message(
    testbed: ChannelsTestbed,
    channel: ChannelDocument,
    user_id: str,
    kind: OutboundMessageKind,
    text: str = "See you at 19:00.",
    message_template: OutboundTemplate | None = None,
) -> OutboundMessageDocument:
    """One message to a customer in the outbox, with its delivery job."""

    now = testbed.clock.now_microseconds()
    key = OutboundIdempotencyKey(f"test:{uuid4()}")
    recipient = ChannelUserId(user_id)
    return queue_outbound_message(
        testbed.outbound_message_repo,
        testbed.job_queue,
        OutboundMessageDocument(
            id=derive_outbound_message_id(channel.business_id, key),
            business_id=channel.business_id,
            kind=kind,
            idempotency_key=key,
            recipient_key=customer_recipient_key(channel.id, recipient),
            customer=CustomerRecipient(
                channel_id=channel.id,
                channel=channel.kind,
                channel_user_id=recipient,
            ),
            text=MessageText(text),
            template=message_template,
            created_at=now,
            updated_at=now,
        ),
        None,
    )
