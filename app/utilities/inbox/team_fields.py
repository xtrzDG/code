"""
The team inbox fields of a conversation: which of them only their own
operations change, and whether the conversation waits for the team.
"""

from app.schemas.constants.conversations import ConversationStatus
from app.schemas.domain.conversations import ConversationDocument
from app.schemas.typings.inbox.booleans import AwaitsTeam
from app.utilities.conversations.review_fields import (
    REVIEW_OWNED_FIELDS,
    with_review_attention,
)

# Changed only by assignment and request bookkeeping; a plain save of the
# conversation keeps what is stored.
TEAM_OWNED_FIELDS: tuple[str, ...] = (
    "assignee_user_id",
    "assigned_by",
    "assigned_at",
    "assignment_revision",
    "has_open_request",
)


def awaits_team(conversation: ConversationDocument) -> AwaitsTeam:
    """A person is needed (HANDOFF) or a request is open."""

    return (
        conversation.status is ConversationStatus.HANDOFF
        or conversation.has_open_request
    )


def with_team_attention(conversation: ConversationDocument) -> ConversationDocument:
    """The conversation with `awaits_team` derived from its other fields."""

    derived: AwaitsTeam = awaits_team(conversation)
    if conversation.awaits_team == derived:
        return conversation

    return conversation.model_copy(update={"awaits_team": derived})


def keep_team_fields(
    incoming: ConversationDocument,
    stored: ConversationDocument,
) -> ConversationDocument:
    """
    What a plain save writes over the stored conversation: everything of
    `incoming` but the team-owned and review fields, which stay as stored
    (a turn that read the conversation before someone assigned or rated it
    must not undo that), and `awaits_team` and `awaits_improvement`
    derived again.
    """

    return with_review_attention(
        with_team_attention(
            incoming.model_copy(
                update={
                    field: getattr(stored, field)
                    for field in (*TEAM_OWNED_FIELDS, *REVIEW_OWNED_FIELDS)
                }
            )
        )
    )
