"""
How a guest's confirmation reaches the chat the booking was made in: the
website chat's widget shows it as a message of the conversation (the widget
reads its conversation, nothing is sent), a messenger gets it through the
outbox with retries, held a few seconds so the assistant's own answer,
written after the tool call, normally arrives first (the widget shows the
confirmation as soon as it is written, just above that answer). WhatsApp,
Messenger and Instagram carry free text only within 24 hours of the
guest's last message there; after that WhatsApp takes the approved
confirmation template, the others cannot carry it.
"""

import hashlib
import logging
from dataclasses import dataclass
from uuid import UUID

from typed_time_provider import Microseconds, WallClock

from app.contracts.jobs import JobQueueFacilitatorContract
from app.contracts.live_events import EventPublisherFacilitatorContract
from app.contracts.repositories.business_repositories import ChannelRepoContract
from app.contracts.repositories.conversation_repositories import (
    ContactRepoContract,
    ConversationRepoContract,
    MessageRepoContract,
)
from app.contracts.repositories.delivery_repositories import (
    OutboundMessageRepoContract,
)
from app.contracts.storage import StorageUnitOfWorkContract
from app.schemas.constants.channels import ChannelKind, MessageDirection
from app.schemas.constants.conversations import MessageAuthor
from app.schemas.constants.deliveries import OutboundMessageKind
from app.schemas.constants.live_events import LiveEventKind
from app.schemas.domain.bookings import BookingDocument
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.domain.channels import ChannelDocument
from app.schemas.domain.contacts import ContactDocument
from app.schemas.domain.conversations import ConversationDocument, MessageDocument
from app.schemas.domain.outbound_messages import (
    CustomerRecipient,
    OutboundMessageDocument,
    OutboundTemplate,
)
from app.schemas.typings.channels.constrained_strings import WhatsAppTemplateName
from app.schemas.typings.conversations.prefixed_id import MessageId
from app.schemas.typings.conversations.strings import MessageText
from app.schemas.typings.deliveries.constrained_strings import OutboundIdempotencyKey
from app.schemas.typings.localization.constrained_strings import LanguageTag
from app.use_cases.shared.messaging_window import (
    WINDOWED_CHANNELS,
    is_messaging_window_open,
)
from app.use_cases.shared.outbox_queue import queue_outbound_message
from app.utilities.channels.channel_health import is_channel_active
from app.utilities.channels.delivery_targets import find_business_channel
from app.utilities.channels.language_codes import to_whatsapp_template_language
from app.utilities.deliveries.delivery_keys import (
    customer_recipient_key,
    derive_outbound_message_id,
)

logger: logging.Logger = logging.getLogger(__name__)

# Chats a confirmation can reach (the phone has its own written
# confirmation after the call).
CONFIRMABLE_CHANNELS: frozenset[ChannelKind] = frozenset(
    {
        ChannelKind.WEB_CHAT,
        ChannelKind.TELEGRAM,
        ChannelKind.WHATSAPP,
        ChannelKind.MESSENGER,
        ChannelKind.INSTAGRAM,
    }
)
# A messenger confirmation waits this long, so the assistant's answer,
# queued after the tool call, normally goes first (a held message never
# blocks the ones queued after it).
CONFIRMATION_HOLD_SECONDS: int = 5
MICROSECONDS_PER_SECOND: int = 1_000_000
# Fixed namespace of the widget confirmations' message ids (never change it:
# a confirmation sent again must find the message it already wrote).
WIDGET_CONFIRMATION_NAMESPACE: UUID = UUID("4d6c1f0e-8a2b-4f37-9b5e-2c7a1d9e3f61")
UUID_BYTES: int = 16


def confirmation_key(booking: BookingDocument) -> OutboundIdempotencyKey:
    """One confirmation per booking and start time: a move is confirmed anew."""

    return OutboundIdempotencyKey(
        f"booking_confirmation:{booking.id}:{int(booking.starts_at)}"
    )


def widget_confirmation_id(
    business: BusinessDocument, booking: BookingDocument
) -> MessageId:
    """
    The widget message of one confirmation: the same booking and start, the
    same id (message ids are version-4 UUIDs, so the digest takes that shape).
    """

    digest: bytes = hashlib.sha256(
        f"{WIDGET_CONFIRMATION_NAMESPACE}|{business.id}|{confirmation_key(booking)}".encode()
    ).digest()
    return MessageId(UUID(bytes=digest[:UUID_BYTES], version=4))


@dataclass(frozen=True)
class ConfirmationLetter:
    """A confirmation ready to go: its text and, for WhatsApp, its template."""

    text: MessageText
    template_parameters: list[MessageText] | None
    language: LanguageTag


@dataclass(frozen=True)
class BookingConfirmationDelivery:
    """Puts a confirmation where the guest's chat shows it (module docstring)."""

    contact_repo: ContactRepoContract
    conversation_repo: ConversationRepoContract
    message_repo: MessageRepoContract
    channel_repo: ChannelRepoContract
    outbound_message_repo: OutboundMessageRepoContract
    job_queue: JobQueueFacilitatorContract
    live_events: EventPublisherFacilitatorContract
    unit_of_work: StorageUnitOfWorkContract | None
    wall_clock: WallClock[Microseconds]
    whatsapp_template: WhatsAppTemplateName | None

    def deliver(
        self,
        business: BusinessDocument,
        conversation: ConversationDocument,
        booking: BookingDocument,
        letter: ConfirmationLetter,
    ) -> bool:
        """True when the guest's chat shows it or the outbox holds it."""

        if conversation.channel is ChannelKind.WEB_CHAT:
            return self._show_in_widget(business, conversation, booking, letter)

        return self._queue(business, conversation, booking, letter)

    def _show_in_widget(
        self,
        business: BusinessDocument,
        conversation: ConversationDocument,
        booking: BookingDocument,
        letter: ConfirmationLetter,
    ) -> bool:
        message_id: MessageId = widget_confirmation_id(business, booking)
        if self.message_repo.get(business.id, message_id) is None:
            now: Microseconds = self.wall_clock.now_unix()
            self.message_repo.save(
                MessageDocument(
                    id=message_id,
                    conversation_id=conversation.id,
                    business_id=business.id,
                    direction=MessageDirection.OUTBOUND,
                    author=MessageAuthor.SYSTEM,
                    text=letter.text,
                    language=letter.language,
                    channel=ChannelKind.WEB_CHAT,
                    created_at=now,
                    updated_at=now,
                )
            )
            self.live_events.publish(
                business.id, LiveEventKind.CONVERSATION_MESSAGE, (conversation.id,)
            )

        return True

    def _queue(
        self,
        business: BusinessDocument,
        conversation: ConversationDocument,
        booking: BookingDocument,
        letter: ConfirmationLetter,
    ) -> bool:
        channel: ChannelDocument | None = find_business_channel(
            self.channel_repo, business.id, conversation.channel
        )
        if channel is None or not is_channel_active(channel):
            logger.info(
                "Booking confirmation through %s skipped: the channel is not "
                "connected.",
                conversation.channel.value,
            )
            return False

        now: Microseconds = self.wall_clock.now_unix()
        template: OutboundTemplate | None = None
        if conversation.channel in WINDOWED_CHANNELS and not self._is_window_open(
            business, conversation, now
        ):
            template = self._template(conversation.channel, letter)
            if template is None:
                return False

        key: OutboundIdempotencyKey = confirmation_key(booking)
        queue_outbound_message(
            self.outbound_message_repo,
            self.job_queue,
            OutboundMessageDocument(
                id=derive_outbound_message_id(business.id, key),
                business_id=business.id,
                kind=OutboundMessageKind.BOOKING_CONFIRMATION,
                idempotency_key=key,
                recipient_key=customer_recipient_key(
                    channel.id, conversation.channel_user_id
                ),
                customer=CustomerRecipient(
                    channel_id=channel.id,
                    channel=conversation.channel,
                    channel_user_id=conversation.channel_user_id,
                ),
                text=letter.text,
                template=template,
                conversation_id=conversation.id,
                booking_id=booking.id,
                next_attempt_at=Microseconds(
                    int(now) + CONFIRMATION_HOLD_SECONDS * MICROSECONDS_PER_SECOND
                ),
                send_before=Microseconds(
                    int(booking.starts_at) * MICROSECONDS_PER_SECOND
                ),
                created_at=now,
                updated_at=now,
            ),
            self.unit_of_work,
        )
        return True

    def _is_window_open(
        self,
        business: BusinessDocument,
        conversation: ConversationDocument,
        now: Microseconds,
    ) -> bool:
        contact: ContactDocument | None = self.contact_repo.get(
            business.id, conversation.contact_id
        )
        return contact is not None and is_messaging_window_open(
            self.conversation_repo,
            self.message_repo,
            business,
            contact,
            conversation.channel,
            now,
        )

    def _template(
        self,
        channel: ChannelKind,
        letter: ConfirmationLetter,
    ) -> OutboundTemplate | None:
        """The WhatsApp confirmation template, when one is configured."""

        if (
            channel is not ChannelKind.WHATSAPP
            or self.whatsapp_template is None
            or letter.template_parameters is None
        ):
            logger.info(
                "Booking confirmation through %s skipped: the guest wrote there "
                "more than 24 hours ago and no confirmation template can carry it.",
                channel.value,
            )
            return None

        return OutboundTemplate(
            name=self.whatsapp_template,
            language_code=to_whatsapp_template_language(letter.language),
            body_parameters=letter.template_parameters,
        )
