"""
A staff reply's way to the customer: the outbox message that carries it
through the conversation's channel (free text, or the owner's WhatsApp
template after the 24-hour window), sent by the worker with retries.
"""

from dataclasses import dataclass

from typed_time_provider import Microseconds

from app.contracts.repositories.business_repositories import ChannelRepoContract
from app.schemas.constants.conversations import StaffReplyBlock
from app.schemas.constants.deliveries import OutboundMessageKind
from app.schemas.domain.channels import ChannelDocument
from app.schemas.domain.conversations import ConversationDocument, MessageDocument
from app.schemas.domain.outbound_messages import (
    CustomerRecipient,
    OutboundMessageDocument,
    OutboundTemplate,
)
from app.schemas.dto.staff_reply_templates import StaffReplyTemplateView
from app.schemas.exceptions.application_errors import (
    ConflictError,
    ValidationFailedError,
)
from app.schemas.typings.conversations.constrained_strings import (
    StaffTemplateReplyText,
)
from app.schemas.typings.conversations.strings import MessageText
from app.utilities.channels.channel_health import is_channel_active
from app.utilities.channels.delivery_targets import find_business_channel
from app.utilities.conversations.staff_replies import (
    describe_block,
    to_template_parameter,
)
from app.utilities.deliveries.customer_message_keys import (
    staff_reply_idempotency_key,
)
from app.utilities.deliveries.delivery_keys import (
    customer_recipient_key,
    derive_outbound_message_id,
)


def template_reply_text(text: str, template: StaffReplyTemplateView) -> MessageText:
    """
    The staff text as the template's single body parameter (one line);
    ValidationFailedError when it is longer than the parameter allows.
    """

    try:
        parameter: StaffTemplateReplyText = to_template_parameter(text)
    except ValueError as error:
        raise ValidationFailedError(
            "A message sent as a WhatsApp template may have at most "
            f"{template.max_text_length} characters (line breaks are sent "
            "as spaces)."
        ) from error

    return MessageText(str(parameter))


@dataclass(frozen=True)
class StaffReplyOutbox:
    """Builds the outbox message of a stored staff reply."""

    channel_repo: ChannelRepoContract

    def build(
        self,
        conversation: ConversationDocument,
        reply: MessageDocument,
        template: StaffReplyTemplateView | None,
        now: Microseconds,
    ) -> OutboundMessageDocument:
        """
        One outbox message per reply (its id derives from the reply's), to
        the customer in the business's channel as it is connected now.
        ConflictError when that channel was disconnected meanwhile.
        """

        channel: ChannelDocument | None = find_business_channel(
            self.channel_repo, conversation.business_id, conversation.channel
        )
        if channel is None or not is_channel_active(channel):
            raise ConflictError(describe_block(StaffReplyBlock.CHANNEL_DISCONNECTED))

        idempotency_key = staff_reply_idempotency_key(reply.id)
        return OutboundMessageDocument(
            id=derive_outbound_message_id(conversation.business_id, idempotency_key),
            business_id=conversation.business_id,
            kind=OutboundMessageKind.STAFF_REPLY,
            idempotency_key=idempotency_key,
            recipient_key=customer_recipient_key(
                channel.id, conversation.channel_user_id
            ),
            customer=CustomerRecipient(
                channel_id=channel.id,
                channel=conversation.channel,
                channel_user_id=conversation.channel_user_id,
            ),
            text=reply.text,
            template=(
                None
                if template is None
                else OutboundTemplate(
                    name=template.name,
                    language_code=template.language_code,
                    body_parameters=[reply.text],
                )
            ),
            conversation_id=conversation.id,
            source_message_id=reply.id,
            created_at=now,
            updated_at=now,
        )
