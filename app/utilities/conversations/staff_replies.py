"""
When staff can write to a customer from the cabinet (concept section 6).

Telegram has no messaging window. WhatsApp, Instagram and Messenger accept
free-form messages only within 24 hours of the customer's last message.
The website chat keeps staff messages for the widget, which fetches them.
Phone conversations have no written way back, test conversations have no
customer, and a channel that is no longer connected carries nothing.
"""

from typed_time_provider import Microseconds

from app.schemas.constants.channels import ChannelKind
from app.schemas.constants.conversations import StaffMessageDelivery, StaffReplyBlock
from app.schemas.domain.conversations import ConversationDocument
from app.schemas.dto.conversation_feed import StaffReplyView
from app.schemas.typings.channels.booleans import IsChannelConnected

CUSTOMER_SERVICE_WINDOW_MICROSECONDS: int = 24 * 60 * 60 * 1_000_000
WINDOWED_CHANNELS: frozenset[ChannelKind] = frozenset(
    {ChannelKind.WHATSAPP, ChannelKind.INSTAGRAM, ChannelKind.MESSENGER}
)
SENDING_CHANNELS: frozenset[ChannelKind] = WINDOWED_CHANNELS | {ChannelKind.TELEGRAM}
BLOCK_MESSAGES: dict[StaffReplyBlock, str] = {
    StaffReplyBlock.TEST_CONVERSATION: (
        "This is a test conversation; there is no customer to write to."
    ),
    StaffReplyBlock.VOICE_CALL: (
        "This conversation was a phone call; call the customer back instead."
    ),
    StaffReplyBlock.UNSUPPORTED_CHANNEL: (
        "Messages cannot be sent from the cabinet through this channel."
    ),
    StaffReplyBlock.CHANNEL_DISCONNECTED: (
        "The channel of this conversation is not connected any more; "
        "reconnect it to write to the customer."
    ),
    StaffReplyBlock.WINDOW_CLOSED: (
        "The customer wrote more than 24 hours ago: this channel accepts "
        "messages from the business only within 24 hours of the customer's "
        "last message. Wait for the customer to write again, or call them."
    ),
}


def assess_staff_reply(
    conversation: ConversationDocument,
    is_channel_connected: IsChannelConnected,
    last_customer_message_at: Microseconds | None,
    now: Microseconds,
) -> StaffReplyView:
    """Whether and how a staff message can reach the conversation's customer."""

    if conversation.is_sandbox or conversation.channel is ChannelKind.OWNER_TEST:
        return blocked(StaffReplyBlock.TEST_CONVERSATION)

    if conversation.channel is ChannelKind.PHONE:
        return blocked(StaffReplyBlock.VOICE_CALL)

    if (
        conversation.channel is not ChannelKind.WEB_CHAT
        and conversation.channel not in SENDING_CHANNELS
    ):
        return blocked(StaffReplyBlock.UNSUPPORTED_CHANNEL)

    if not is_channel_connected:
        return blocked(StaffReplyBlock.CHANNEL_DISCONNECTED)

    if conversation.channel is ChannelKind.WEB_CHAT:
        return StaffReplyView(
            is_available=True,
            delivery=StaffMessageDelivery.STORED_FOR_WIDGET,
        )

    if conversation.channel not in WINDOWED_CHANNELS:
        return StaffReplyView(is_available=True, delivery=StaffMessageDelivery.SENT)

    closes_at: Microseconds | None = (
        None
        if last_customer_message_at is None
        else Microseconds(
            int(last_customer_message_at) + CUSTOMER_SERVICE_WINDOW_MICROSECONDS
        )
    )
    if closes_at is None or int(closes_at) <= int(now):
        return StaffReplyView(
            is_available=False,
            block=StaffReplyBlock.WINDOW_CLOSED,
            window_closes_at=closes_at,
        )

    return StaffReplyView(
        is_available=True,
        delivery=StaffMessageDelivery.SENT,
        window_closes_at=closes_at,
    )


def blocked(block: StaffReplyBlock) -> StaffReplyView:
    return StaffReplyView(is_available=False, block=block)


def describe_block(block: StaffReplyBlock) -> str:
    """Why staff cannot write now, in English (the API error message)."""

    return BLOCK_MESSAGES[block]
