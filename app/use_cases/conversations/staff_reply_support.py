"""Whether staff can write to a conversation's customer now, from storage."""

from typed_time_provider import Microseconds

from app.contracts.repositories import (
    ChannelRepoContract,
    ConversationRepoContract,
    MessageRepoContract,
)
from app.schemas.constants.channels import ChannelStatus, MessageDirection
from app.schemas.domain.channels import ChannelDocument
from app.schemas.domain.conversations import ConversationDocument
from app.schemas.dto.conversation_feed import StaffReplyView
from app.utilities.channels.delivery_targets import find_business_channel
from app.utilities.conversations.staff_replies import (
    CUSTOMER_SERVICE_WINDOW_MICROSECONDS,
    assess_staff_reply,
)


def assess_conversation_reply(
    conversation: ConversationDocument,
    conversation_repo: ConversationRepoContract,
    message_repo: MessageRepoContract,
    channel_repo: ChannelRepoContract,
    now: Microseconds,
) -> StaffReplyView:
    """
    The staff reply state of a conversation: the business's channel must be
    connected, and for windowed channels the customer's last message in
    that channel (in this or a later conversation) sets the window.
    """

    channel: ChannelDocument | None = find_business_channel(
        channel_repo, conversation.business_id, conversation.channel
    )
    return assess_staff_reply(
        conversation,
        channel is not None and channel.status is ChannelStatus.CONNECTED,
        last_customer_message_at(conversation, conversation_repo, message_repo, now),
        now,
    )


def last_customer_message_at(
    conversation: ConversationDocument,
    conversation_repo: ConversationRepoContract,
    message_repo: MessageRepoContract,
    now: Microseconds,
) -> Microseconds | None:
    """
    When the customer last wrote in the conversation's channel; only
    messages inside the last 24 hours matter, so older conversations are
    not read.
    """

    window_start: int = int(now) - CUSTOMER_SERVICE_WINDOW_MICROSECONDS
    latest: Microseconds | None = None
    for candidate in conversation_repo.list_by_business(conversation.business_id):
        if (
            candidate.contact_id != conversation.contact_id
            or candidate.channel is not conversation.channel
            or candidate.is_sandbox != conversation.is_sandbox
            or int(candidate.last_message_at) < window_start
        ):
            continue

        for message in message_repo.list_by_conversation(
            conversation.business_id, candidate.id
        ):
            if message.direction is MessageDirection.INBOUND and (
                latest is None or int(message.created_at) > int(latest)
            ):
                latest = message.created_at

    return latest
