"""
The 24-hour window in which a messenger accepts free-form messages: a
message the business starts (a reminder, a confirmation after a call)
goes as free text only inside it.
"""

from typed_time_provider import Microseconds

from app.contracts.repositories.conversation_repositories import (
    ConversationRepoContract,
    MessageRepoContract,
)
from app.schemas.constants.channels import ChannelKind, MessageDirection
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.domain.contacts import ContactDocument

MICROSECONDS_PER_SECOND: int = 1_000_000
# Free-form messages are allowed within 24 hours of the customer's last
# message in WhatsApp, Messenger and Instagram (concept section 6); later
# a WhatsApp reminder is an approved template, and the other two skip.
CUSTOMER_SERVICE_WINDOW_SECONDS: int = 24 * 60 * 60
WINDOWED_CHANNELS: frozenset[ChannelKind] = frozenset(
    {ChannelKind.WHATSAPP, ChannelKind.MESSENGER, ChannelKind.INSTAGRAM}
)


def is_messaging_window_open(
    conversation_repo: ConversationRepoContract,
    message_repo: MessageRepoContract,
    business: BusinessDocument,
    contact: ContactDocument,
    channel: ChannelKind,
    now: Microseconds,
) -> bool:
    """Did the customer write in this channel within the last 24 hours?"""

    window_start: int = int(now) - (
        CUSTOMER_SERVICE_WINDOW_SECONDS * MICROSECONDS_PER_SECOND
    )
    for conversation in conversation_repo.list_by_contact(
        business.id, contact.id, last_message_from=Microseconds(window_start)
    ):
        if conversation.channel is not channel or conversation.is_sandbox:
            continue

        for message in message_repo.list_by_conversation(business.id, conversation.id):
            if (
                message.direction is MessageDirection.INBOUND
                and int(message.created_at) >= window_start
            ):
                return True

    return False
