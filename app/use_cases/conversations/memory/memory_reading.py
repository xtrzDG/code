"""What the customer memory reads of a customer's earlier conversations."""

from app.contracts.repositories.booking_repositories import LeadRepoContract
from app.contracts.repositories.inbox_repositories import (
    ConversationNoteRepoContract,
)
from app.schemas.constants.bookings import LeadStatus
from app.schemas.domain.conversations import ConversationDocument
from app.schemas.dto.bookings import LeadView
from app.schemas.dto.customer_memory.returning_customers import (
    RememberedConversation,
    RememberedNote,
)
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.conversations.constrained_strings import (
    ConversationSummaryText,
)
from app.schemas.typings.storage.constrained_integers import DocumentQueryLimit
from app.use_cases.shared.lead_views import build_lead_view
from app.utilities.conversations.memory_facts import keep_memory_facts

# The latest conversations whose summaries, requests and notes are read.
RECALLED_CONVERSATION_COUNT: int = 10
MAX_SUMMARIES: int = 3
MAX_UPCOMING_BOOKINGS: DocumentQueryLimit = DocumentQueryLimit(3)
MAX_OPEN_LEADS: int = 3
MAX_TEAM_NOTES: int = 3
# Requests and notes are looked up in this many of the latest conversations.
LOOKUP_CONVERSATION_COUNT: int = 3
OPEN_LEAD_STATUSES: frozenset[LeadStatus] = frozenset(
    {LeadStatus.NEW, LeadStatus.IN_PROGRESS}
)


def remembered_summaries(
    earlier: list[ConversationDocument],
) -> list[RememberedConversation]:
    """
    The summaries of the latest earlier conversations, the latest first;
    a sentence stored before the memory filter that instructs the
    assistant or claims a rule is left out here too (`keep_memory_facts`).
    """

    remembered: list[RememberedConversation] = []
    for conversation in earlier:
        summary: ConversationSummaryText | None = keep_memory_facts(
            conversation.summary
        )
        if summary is not None:
            remembered.append(
                RememberedConversation(
                    last_message_at=conversation.last_message_at,
                    channel=conversation.channel,
                    summary=summary,
                )
            )

    return remembered[:MAX_SUMMARIES]


def open_leads(
    lead_repo: LeadRepoContract,
    business_id: BusinessId,
    conversations: list[ConversationDocument],
) -> list[LeadView]:
    """Requests staff have not closed, made in the latest conversations."""

    leads: list[LeadView] = [
        build_lead_view(lead)
        for conversation in conversations[:LOOKUP_CONVERSATION_COUNT]
        for lead in lead_repo.list_by_conversation(business_id, conversation.id)
        if lead.status in OPEN_LEAD_STATUSES and not lead.is_sandbox
    ]
    return leads[:MAX_OPEN_LEADS]


def team_notes(
    note_repo: ConversationNoteRepoContract,
    business_id: BusinessId,
    conversations: list[ConversationDocument],
) -> list[RememberedNote]:
    """The team's latest notes on the latest conversations, the newest first."""

    notes: list[RememberedNote] = [
        RememberedNote(created_at=note.created_at, text=note.text)
        for conversation in conversations[:LOOKUP_CONVERSATION_COUNT]
        for note in note_repo.list_by_conversation(business_id, conversation.id)
    ]
    return sorted(notes, key=lambda note: int(note.created_at), reverse=True)[
        :MAX_TEAM_NOTES
    ]
