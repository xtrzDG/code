"""One reminder through one of the customer's messenger identities."""

import logging
from dataclasses import dataclass

from typed_time_provider import Microseconds, WallClock

from app.contracts.jobs import JobQueueFacilitatorContract
from app.contracts.repositories.business_repositories import ChannelRepoContract
from app.contracts.repositories.conversation_repositories import (
    ConversationRepoContract,
    MessageRepoContract,
)
from app.contracts.repositories.delivery_repositories import (
    OutboundMessageRepoContract,
)
from app.contracts.storage import StorageUnitOfWorkContract
from app.contracts.transformer_contract import TransformerContract
from app.schemas.constants.bookings import BookingReminderKind
from app.schemas.constants.channels import ChannelKind
from app.schemas.constants.deliveries import OutboundMessageKind
from app.schemas.domain.bookings import BookingDocument
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.domain.channels import ChannelDocument
from app.schemas.domain.contacts import ChannelIdentity, ContactDocument
from app.schemas.domain.outbound_messages import (
    CustomerRecipient,
    OutboundMessageDocument,
    OutboundTemplate,
)
from app.schemas.dto.operations.message_texts import BookingMessageInput
from app.schemas.typings.channels.constrained_strings import WhatsAppTemplateName
from app.schemas.typings.conversations.strings import MessageText
from app.schemas.typings.deliveries.constrained_strings import OutboundIdempotencyKey
from app.schemas.typings.deliveries.prefixed_id import OutboundMessageId
from app.use_cases.shared.messaging_window import (
    WINDOWED_CHANNELS,
    is_messaging_window_open,
)
from app.use_cases.shared.outbox_queue import queue_outbound_message
from app.utilities.channels.channel_health import is_channel_active
from app.utilities.channels.delivery_targets import find_business_channel
from app.utilities.channels.language_codes import to_whatsapp_template_language
from app.utilities.deliveries.customer_message_keys import reminder_idempotency_key
from app.utilities.deliveries.delivery_keys import (
    customer_recipient_key,
    derive_outbound_message_id,
)

logger: logging.Logger = logging.getLogger(__name__)


def reminder_key(booking: BookingDocument) -> OutboundIdempotencyKey:
    """The day-before reminder of the booking's current start time."""

    return reminder_idempotency_key(
        booking.id, BookingReminderKind.DAY_BEFORE, booking.starts_at
    )


def reminder_message_id(booking: BookingDocument) -> OutboundMessageId:
    return derive_outbound_message_id(booking.business_id, reminder_key(booking))


@dataclass(frozen=True)
class ReminderDelivery:
    """
    Free text where the channel takes it (Telegram; WhatsApp, Messenger
    and Instagram within 24 hours of the customer's last message there),
    the approved WhatsApp template later; Messenger and Instagram outside
    the window cannot carry it. The reminder goes into the outbox (once
    per booking and start time: a run that comes again after a restart
    finds it queued) and the worker sends it with retries.
    """

    conversation_repo: ConversationRepoContract
    message_repo: MessageRepoContract
    channel_repo: ChannelRepoContract
    outbound_message_repo: OutboundMessageRepoContract
    job_queue: JobQueueFacilitatorContract
    unit_of_work: StorageUnitOfWorkContract | None
    reminder_transformer: TransformerContract[BookingMessageInput, MessageText]
    reminder_template_transformer: TransformerContract[
        BookingMessageInput, list[MessageText]
    ]
    wall_clock: WallClock[Microseconds]
    whatsapp_reminder_template: WhatsAppTemplateName | None

    def is_queued(self, booking: BookingDocument) -> bool:
        """
        The reminder of the booking's current start time is in the outbox
        already (a run before a crash queued it but did not mark it).
        """

        return (
            self.outbound_message_repo.get(
                booking.business_id, reminder_message_id(booking)
            )
            is not None
        )

    def deliver(
        self,
        business: BusinessDocument,
        contact: ContactDocument,
        identity: ChannelIdentity,
        booking: BookingDocument,
        message_input: BookingMessageInput,
    ) -> bool:
        """
        Queue the reminder for one identity; False when that channel cannot
        carry it (not connected, or its window closed without a template).
        """

        channel: ChannelDocument | None = find_business_channel(
            self.channel_repo, business.id, identity.channel
        )
        if channel is None or not is_channel_active(channel):
            logger.info(
                "Reminder through %s skipped: the channel is not connected.",
                identity.channel.value,
            )
            return False

        now: Microseconds = self.wall_clock.now_unix()
        template: OutboundTemplate | None = None
        if identity.channel in WINDOWED_CHANNELS and not is_messaging_window_open(
            self.conversation_repo,
            self.message_repo,
            business,
            contact,
            identity.channel,
            now,
        ):
            template = self._template(identity, message_input)
            if template is None:
                return False

        idempotency_key = reminder_key(booking)
        queue_outbound_message(
            self.outbound_message_repo,
            self.job_queue,
            OutboundMessageDocument(
                id=reminder_message_id(booking),
                business_id=business.id,
                kind=OutboundMessageKind.BOOKING_REMINDER,
                idempotency_key=idempotency_key,
                recipient_key=customer_recipient_key(
                    channel.id, identity.channel_user_id
                ),
                customer=CustomerRecipient(
                    channel_id=channel.id,
                    channel=identity.channel,
                    channel_user_id=identity.channel_user_id,
                ),
                text=self.reminder_transformer.transform(message_input),
                template=template,
                booking_id=booking.id,
                created_at=now,
                updated_at=now,
            ),
            self.unit_of_work,
        )
        return True

    def _template(
        self,
        identity: ChannelIdentity,
        message_input: BookingMessageInput,
    ) -> OutboundTemplate | None:
        """The WhatsApp reminder template, when one is configured."""

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
            return None

        return OutboundTemplate(
            name=self.whatsapp_reminder_template,
            language_code=to_whatsapp_template_language(message_input.language),
            body_parameters=self.reminder_template_transformer.transform(message_input),
        )
