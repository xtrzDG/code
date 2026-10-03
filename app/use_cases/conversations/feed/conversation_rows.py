"""The rows of a page of conversations, read for that page only."""

from collections.abc import Sequence

from app.contracts.repositories.conversation_repositories import (
    ContactRepoContract,
    MessageRepoContract,
)
from app.schemas.domain.contacts import ContactDocument
from app.schemas.domain.conversations import ConversationDocument, MessageDocument
from app.schemas.dto.conversation_feed.conversation_views import ConversationViewSource
from app.schemas.dto.conversation_feed.message_tallies import ConversationMessageTally
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.contacts.prefixed_id import ContactId
from app.schemas.typings.conversations.prefixed_id import ConversationId


def build_view_sources(
    business_id: BusinessId,
    conversations: Sequence[ConversationDocument],
    contact_repo: ContactRepoContract,
    message_repo: MessageRepoContract,
    contacts: dict[ContactId, ContactDocument] | None = None,
) -> list[ConversationViewSource]:
    """
    Each conversation with its contact, its message counts (one grouped
    count for the page) and its newest written message (one statement with
    an indexed probe per conversation), never every message of them.
    """

    known: dict[ContactId, ContactDocument] = (
        contact_repo.get_many(
            business_id, [conversation.contact_id for conversation in conversations]
        )
        if contacts is None
        else contacts
    )
    tallies: dict[ConversationId, ConversationMessageTally] = (
        message_repo.tally_conversations(
            business_id, [conversation.id for conversation in conversations]
        )
    )
    latest: dict[ConversationId, MessageDocument] = message_repo.find_latest_written(
        business_id, [conversation.id for conversation in conversations]
    )
    return [
        ConversationViewSource(
            conversation=conversation,
            contact=known.get(conversation.contact_id),
            tally=tallies.get(conversation.id, ConversationMessageTally()),
            last_written=latest.get(conversation.id),
        )
        for conversation in conversations
    ]
