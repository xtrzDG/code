"""
A widget poll's reads through the repositories: what
`WidgetPollReadAdapterContract` reads in one statement on Postgres, for the
storage without it (in memory, where there are no round trips to save).
"""

from app.contracts.repositories.conversation_repositories import (
    ConversationRepoContract,
    MessageRepoContract,
)
from app.contracts.repositories.spend_guard_repositories import (
    BusinessLimitsRepoContract,
)
from app.schemas.constants.channels import ChannelKind
from app.schemas.domain.conversations import ConversationDocument, MessageDocument
from app.schemas.dto.channels.widget_poll_reads import WidgetPollRead
from app.schemas.dto.message_positions import MessagePosition
from app.schemas.dto.paging import KeysetSlice
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.conversations.prefixed_id import MessageId
from app.schemas.typings.conversations.strings import ChannelUserId
from app.schemas.typings.platform.constrained_integers import KeysetReadLimit
from app.use_cases.channels.widget_message_window import ids_after_cursor


def read_poll_through_repositories(
    conversation_repo: ConversationRepoContract,
    message_repo: MessageRepoContract,
    business_limits_repo: BusinessLimitsRepoContract,
    business_id: BusinessId,
    visitor: ChannelUserId,
    after: MessageId | None,
    window: KeysetReadLimit,
) -> WidgetPollRead:
    """
    The business's allowed websites, the visitor's web-chat conversations
    without the sandbox ones (the current first), the positions of their
    newest `window` messages (only with a cursor: a poll without one reads
    the whole chat) and, in full, those after the cursor.
    """

    allowed = business_limits_repo.get_or_default(business_id).widget_allowed_origins
    conversations: list[ConversationDocument] = [
        conversation
        for conversation in conversation_repo.list_by_channel_user(
            business_id, ChannelKind.WEB_CHAT, visitor
        )
        if not conversation.is_sandbox
    ]
    if not conversations or after is None:
        return WidgetPollRead(allowed_origins=allowed, conversations=conversations)

    newest: list[MessagePosition] = message_repo.page_newest_positions_of_conversations(
        business_id,
        [conversation.id for conversation in conversations],
        KeysetSlice(limit=window),
    )
    later_ids: list[MessageId] = ids_after_cursor(newest, after)
    found: dict[MessageId, MessageDocument] = (
        message_repo.get_many(business_id, later_ids) if later_ids else {}
    )
    return WidgetPollRead(
        allowed_origins=allowed,
        conversations=conversations,
        newest=newest,
        after_cursor=[
            found[message_id] for message_id in later_ids if message_id in found
        ],
    )
