"""
Where a message the business starts can reach a customer: their identity
in the preferred messenger first (where they asked), then the other
messengers they are known in, each through the business's connected
channel. WhatsApp, Messenger and Instagram take free text only within 24
hours of the customer's last message there; later WhatsApp takes an
approved template (when one is named), the other two cannot carry it.
The waitlist's offers and the rebooking campaigns go this way.
"""

from dataclasses import dataclass
from typing import NamedTuple

from typed_time_provider import Microseconds

from app.contracts.repositories.business_repositories import ChannelRepoContract
from app.contracts.repositories.conversation_repositories import (
    ConversationRepoContract,
    MessageRepoContract,
)
from app.schemas.constants.channels import ChannelKind, MessageDirection
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.domain.channels import ChannelDocument
from app.schemas.domain.contacts import ChannelIdentity, ContactDocument
from app.schemas.typings.channels.constrained_strings import WhatsAppTemplateName
from app.use_cases.shared.messaging_window import (
    CUSTOMER_SERVICE_WINDOW_SECONDS,
    WINDOWED_CHANNELS,
)
from app.utilities.channels.channel_health import is_channel_active
from app.utilities.channels.delivery_targets import find_business_channel

MICROSECONDS_PER_SECOND: int = 1_000_000
# Messengers a business can write to first, best first after the
# preferred one: Telegram has no messaging window; WhatsApp is where most
# customers are.
PROACTIVE_CHANNELS: tuple[ChannelKind, ...] = (
    ChannelKind.TELEGRAM,
    ChannelKind.WHATSAPP,
    ChannelKind.MESSENGER,
    ChannelKind.INSTAGRAM,
)


@dataclass(frozen=True)
class ProactiveRoute:
    """The identity, the business's channel and, outside the window, the template."""

    identity: ChannelIdentity
    channel: ChannelDocument
    template_name: WhatsAppTemplateName | None = None


class RouteChoice(NamedTuple):
    """The route found, or none and whether a closed window was the reason."""

    route: ProactiveRoute | None
    is_window_closed: bool = False


@dataclass(frozen=True)
class ProactiveRouting:
    """Finds a route with the repositories it reads."""

    channel_repo: ChannelRepoContract
    conversation_repo: ConversationRepoContract
    message_repo: MessageRepoContract

    def choose(
        self,
        business: BusinessDocument,
        contact: ContactDocument,
        preferred: ChannelKind | None,
        template_name: WhatsAppTemplateName | None,
        now: Microseconds,
    ) -> RouteChoice:
        """The first identity that can carry the message now, or why none can."""

        is_window_closed: bool = False
        for identity in messenger_identities(contact, preferred):
            channel: ChannelDocument | None = find_business_channel(
                self.channel_repo, business.id, identity.channel
            )
            if channel is None or not is_channel_active(channel):
                continue

            if identity.channel not in WINDOWED_CHANNELS or self.is_window_open(
                business, contact, identity.channel, now
            ):
                return RouteChoice(ProactiveRoute(identity=identity, channel=channel))

            if identity.channel is ChannelKind.WHATSAPP and template_name is not None:
                return RouteChoice(
                    ProactiveRoute(
                        identity=identity, channel=channel, template_name=template_name
                    )
                )

            is_window_closed = True

        return RouteChoice(None, is_window_closed)

    def is_window_open(
        self,
        business: BusinessDocument,
        contact: ContactDocument,
        channel: ChannelKind,
        now: Microseconds,
    ) -> bool:
        """Did the customer write in this channel within the last 24 hours?"""

        window_start = Microseconds(
            int(now) - CUSTOMER_SERVICE_WINDOW_SECONDS * MICROSECONDS_PER_SECOND
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


def messenger_identities(
    contact: ContactDocument, preferred: ChannelKind | None
) -> list[ChannelIdentity]:
    """
    The customer's messenger identities, best first: the preferred
    channel's, then the others. Phone and the website chat cannot carry a
    message the business starts, so they are never used.
    """

    order: tuple[ChannelKind, ...] = (
        PROACTIVE_CHANNELS if preferred is None else (preferred, *PROACTIVE_CHANNELS)
    )
    identities: list[ChannelIdentity] = []
    for channel in order:
        if channel not in PROACTIVE_CHANNELS:
            continue

        for identity in contact.channel_identities:
            if identity.channel is channel and identity not in identities:
                identities.append(identity)

    return identities
