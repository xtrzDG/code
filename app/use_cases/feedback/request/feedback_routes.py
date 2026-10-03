"""
Where a request for feedback can go: the customer's identity in the
booking's own messenger first, then the other messengers they are known
in, each through the business's connected channel. WhatsApp, Messenger and
Instagram take free text only within 24 hours of the customer's last
message there; later WhatsApp takes the owner's approved template, and the
other two cannot carry the request.
"""

from dataclasses import dataclass

from typed_time_provider import Microseconds

from app.contracts.repositories.business_repositories import ChannelRepoContract
from app.contracts.repositories.conversation_repositories import (
    ConversationRepoContract,
    MessageRepoContract,
)
from app.schemas.constants.channels import ChannelKind, MessageDirection
from app.schemas.constants.feedback import FeedbackSkipReason
from app.schemas.domain.bookings import BookingDocument
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.domain.channels import ChannelDocument
from app.schemas.domain.contacts import ChannelIdentity, ContactDocument
from app.schemas.domain.feedback import ReviewSettingsDocument
from app.schemas.typings.channels.constrained_strings import WhatsAppTemplateName
from app.schemas.typings.localization.constrained_strings import LanguageTag
from app.utilities.channels.channel_health import is_channel_active
from app.utilities.channels.delivery_targets import find_business_channel

MICROSECONDS_PER_SECOND: int = 1_000_000
MESSAGING_WINDOW_SECONDS: int = 24 * 60 * 60
# Messengers a request can be written to, best first after the booking's
# own channel: Telegram has no messaging window; WhatsApp is where most
# customers are.
FEEDBACK_CHANNELS: tuple[ChannelKind, ...] = (
    ChannelKind.TELEGRAM,
    ChannelKind.WHATSAPP,
    ChannelKind.MESSENGER,
    ChannelKind.INSTAGRAM,
)
WINDOWED_CHANNELS: frozenset[ChannelKind] = frozenset(
    {ChannelKind.WHATSAPP, ChannelKind.MESSENGER, ChannelKind.INSTAGRAM}
)


@dataclass(frozen=True)
class FeedbackRoute:
    """The identity, the business's channel and, outside the window, the template."""

    identity: ChannelIdentity
    channel: ChannelDocument
    template_name: WhatsAppTemplateName | None = None


@dataclass(frozen=True)
class FeedbackRouting:
    """Finds a route with the repositories it reads."""

    channel_repo: ChannelRepoContract
    conversation_repo: ConversationRepoContract
    message_repo: MessageRepoContract

    def choose(
        self,
        business: BusinessDocument,
        settings: ReviewSettingsDocument,
        contact: ContactDocument,
        booking: BookingDocument,
        now: Microseconds,
    ) -> FeedbackRoute | FeedbackSkipReason:
        """The first identity that can carry the request, or why none can."""

        is_window_closed: bool = False
        for identity in feedback_identities(contact, booking.source_channel):
            channel: ChannelDocument | None = find_business_channel(
                self.channel_repo, business.id, identity.channel
            )
            if channel is None or not is_channel_active(channel):
                continue

            if identity.channel not in WINDOWED_CHANNELS or self.is_window_open(
                business, contact, identity.channel, now
            ):
                return FeedbackRoute(identity=identity, channel=channel)

            if (
                identity.channel is ChannelKind.WHATSAPP
                and settings.feedback_template_name is not None
            ):
                return FeedbackRoute(
                    identity=identity,
                    channel=channel,
                    template_name=settings.feedback_template_name,
                )

            is_window_closed = True

        if is_window_closed:
            return FeedbackSkipReason.WINDOW_CLOSED

        return FeedbackSkipReason.NO_CHANNEL

    def is_window_open(
        self,
        business: BusinessDocument,
        contact: ContactDocument,
        channel: ChannelKind,
        now: Microseconds,
    ) -> bool:
        """Did the customer write in this channel within the last 24 hours?"""

        window_start = Microseconds(
            int(now) - MESSAGING_WINDOW_SECONDS * MICROSECONDS_PER_SECOND
        )
        for conversation in self.conversation_repo.list_by_contact(
            business.id, contact.id, last_message_from=window_start
        ):
            if conversation.channel is not channel or conversation.is_sandbox:
                continue

            written = self.message_repo.count_by_conversation(
                business.id,
                conversation.id,
                MessageDirection.INBOUND,
                created_from=window_start,
            )
            if int(written) > 0:
                return True

        return False


def feedback_identities(
    contact: ContactDocument,
    source_channel: ChannelKind,
) -> list[ChannelIdentity]:
    """
    The customer's messenger identities, best first: the booking's own
    channel, then the others. Phone and web chat cannot carry a message
    later, so they are never used.
    """

    identities: list[ChannelIdentity] = []
    for channel in (source_channel, *FEEDBACK_CHANNELS):
        if channel not in FEEDBACK_CHANNELS:
            continue

        for identity in contact.channel_identities:
            if identity.channel is channel and identity not in identities:
                identities.append(identity)

    return identities


def feedback_language(
    business: BusinessDocument,
    contact: ContactDocument,
    booking: BookingDocument,
) -> LanguageTag:
    """The booking's language, else the customer's, else the business's."""

    return booking.language or contact.language or business.default_language
