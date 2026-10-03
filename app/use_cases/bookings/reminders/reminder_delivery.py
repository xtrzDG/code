"""One reminder through one of the customer's messenger identities."""

import logging
from dataclasses import dataclass

from typed_time_provider import Microseconds, WallClock

from app.contracts.facilitators import ChannelMessageSenderFacilitatorContract
from app.contracts.repositories.conversation_repositories import (
    ConversationRepoContract,
    MessageRepoContract,
)
from app.contracts.transformer_contract import TransformerContract
from app.schemas.constants.channels import ChannelKind
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.domain.contacts import ChannelIdentity, ContactDocument
from app.schemas.dto.operations.message_texts import BookingMessageInput
from app.schemas.typings.channels.constrained_strings import WhatsAppTemplateName
from app.schemas.typings.conversations.strings import MessageText
from app.use_cases.bookings.reminders.messaging_window import (
    WINDOWED_CHANNELS,
    is_messaging_window_open,
)

logger: logging.Logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class ReminderDelivery:
    """
    Free text where the channel takes it (Telegram; WhatsApp, Messenger
    and Instagram within 24 hours of the customer's last message there),
    the approved WhatsApp template later; Messenger and Instagram outside
    the window cannot carry it.
    """

    conversation_repo: ConversationRepoContract
    message_repo: MessageRepoContract
    channel_message_sender: ChannelMessageSenderFacilitatorContract
    reminder_transformer: TransformerContract[BookingMessageInput, MessageText]
    reminder_template_transformer: TransformerContract[
        BookingMessageInput, list[MessageText]
    ]
    wall_clock: WallClock[Microseconds]
    whatsapp_reminder_template: WhatsAppTemplateName | None

    def deliver(
        self,
        business: BusinessDocument,
        contact: ContactDocument,
        identity: ChannelIdentity,
        message_input: BookingMessageInput,
    ) -> bool:
        """Send through one identity; False when that channel cannot carry it."""

        if identity.channel not in WINDOWED_CHANNELS or is_messaging_window_open(
            self.conversation_repo,
            self.message_repo,
            business,
            contact,
            identity.channel,
            self.wall_clock.now_unix(),
        ):
            self.channel_message_sender.send(
                business.id,
                identity.channel,
                identity.channel_user_id,
                self.reminder_transformer.transform(message_input),
            )
            return True

        if (
            identity.channel is not ChannelKind.WHATSAPP
            or self.whatsapp_reminder_template is None
        ):
            logger.info(
                "Reminder through %s skipped: the customer wrote there more than "
                "24 hours ago%s.",
                identity.channel.value,
                (
                    " and WHATSAPP_REMINDER_TEMPLATE is not configured"
                    if identity.channel is ChannelKind.WHATSAPP
                    else ""
                ),
            )
            return False

        self.channel_message_sender.send_whatsapp_template(
            business.id,
            identity.channel_user_id,
            self.whatsapp_reminder_template,
            message_input.language,
            self.reminder_template_transformer.transform(message_input),
        )
        return True
