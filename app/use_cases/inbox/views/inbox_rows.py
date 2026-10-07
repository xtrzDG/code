"""The rows of a page of the team inbox, read for that page only."""

from collections.abc import Sequence

from app.contracts.repositories.conversation_repositories import (
    ContactRepoContract,
    MessageRepoContract,
)
from app.contracts.repositories.inbox_repositories import (
    ConversationNoteRepoContract,
    InboxWorkRepoContract,
)
from app.schemas.constants.conversations import ConversationStatus
from app.schemas.domain.conversations import ConversationDocument
from app.schemas.dto.inbox.inbox_views import InboxItemSource
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.inbox.constrained_integers import ConversationNoteCount


def build_inbox_sources(
    business_id: BusinessId,
    conversations: Sequence[ConversationDocument],
    contact_repo: ContactRepoContract,
    message_repo: MessageRepoContract,
    note_repo: ConversationNoteRepoContract,
    work_repo: InboxWorkRepoContract,
) -> list[InboxItemSource]:
    """
    Each conversation with its contact, newest written message, note count,
    open handoff and newest open request: five statements for the page
    (one read each, with an indexed probe per conversation where needed),
    never one query per row.
    """

    if not conversations:
        return []

    conversation_ids = [conversation.id for conversation in conversations]
    contacts = contact_repo.get_many(
        business_id, [conversation.contact_id for conversation in conversations]
    )
    latest = message_repo.find_latest_written(business_id, conversation_ids)
    notes = note_repo.count_by_conversations(business_id, conversation_ids)
    handoffs = work_repo.latest_open_handoffs(
        business_id,
        [
            conversation.id
            for conversation in conversations
            if conversation.status is ConversationStatus.HANDOFF
        ],
    )
    open_requests = work_repo.latest_open_requests(
        business_id,
        [
            conversation.id
            for conversation in conversations
            if conversation.has_open_request
        ],
    )
    return [
        InboxItemSource(
            conversation=conversation,
            contact=contacts.get(conversation.contact_id),
            last_written=latest.get(conversation.id),
            note_count=notes.get(conversation.id, ConversationNoteCount(0)),
            handoff=handoffs.get(conversation.id),
            request=open_requests.get(conversation.id),
        )
        for conversation in conversations
    ]
