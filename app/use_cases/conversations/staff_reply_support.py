"""Whether staff can write to a conversation's customer now, from storage."""

from typed_time_provider import Microseconds

from app.contracts.repositories.business_repositories import ChannelRepoContract
from app.contracts.repositories.conversation_repositories import (
    ConversationRepoContract,
    MessageRepoContract,
)
from app.schemas.constants.channels import MessageDirection
from app.schemas.domain.channels import ChannelDocument
from app.schemas.domain.conversations import ConversationDocument
from app.schemas.dto.conversation_feed.conversation_views import StaffReplyView
from app.schemas.typings.localization.constrained_strings import LanguageTag
from app.utilities.channels.channel_health import is_channel_active
from app.utilities.channels.delivery_targets import find_business_channel
from app.utilities.channels.staff_templates import (
    channel_staff_templates,
    choose_staff_template,
)
from app.utilities.conversations.staff_replies import (
    CUSTOMER_SERVICE_WINDOW_MICROSECONDS,
    assess_staff_reply,
)


def assess_conversation_reply(
    conversation: ConversationDocument,
    conversation_repo: ConversationRepoContract,
    message_repo: MessageRepoContract,
    channel_repo: ChannelRepoContract,
    default_language: LanguageTag,
    now: Microseconds,
) -> StaffReplyView:
    """
    The staff reply state of a conversation: the business's channel must be
    connected (a channel in ERROR still gets every delivery attempt, and a
    working one clears the error), and for windowed channels the customer's
    last message in that channel (in this or a later conversation) sets the
    window; after it, WhatsApp offers the channel's staff template in the
    conversation's language, else in the business's `default_language`
    (`choose_staff_template`), so a Hebrew customer gets the Hebrew one.
    """

    channel: ChannelDocument | None = find_business_channel(
        channel_repo, conversation.business_id, conversation.channel
    )
    return assess_staff_reply(
        conversation,
        channel is not None and is_channel_active(channel),
        last_customer_message_at(conversation, conversation_repo, message_repo, now),
        now,
        None
        if channel is None
        else choose_staff_template(
            channel_staff_templates(channel),
            conversation.language,
            default_language,
        ),
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

    window_start = Microseconds(int(now) - CUSTOMER_SERVICE_WINDOW_MICROSECONDS)
    latest: Microseconds | None = None
    for candidate in conversation_repo.list_by_contact(
        conversation.business_id,
        conversation.contact_id,
        last_message_from=window_start,
    ):
        if (
            candidate.channel is not conversation.channel
            or candidate.is_sandbox != conversation.is_sandbox
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
