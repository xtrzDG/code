"""The assignment of a conversation as the cabinet reads it."""

from app.schemas.domain.conversations import ConversationDocument
from app.schemas.dto.inbox.assignment import ConversationAssignmentView


def build_assignment_view(
    conversation: ConversationDocument,
) -> ConversationAssignmentView:
    return ConversationAssignmentView(
        conversation_id=conversation.id,
        assignee_user_id=conversation.assignee_user_id,
        assigned_by=conversation.assigned_by,
        assigned_at=conversation.assigned_at,
        is_assigned_automatically=(
            conversation.assignee_user_id is not None
            and conversation.assigned_by is None
        ),
        assignment_revision=conversation.assignment_revision,
    )
