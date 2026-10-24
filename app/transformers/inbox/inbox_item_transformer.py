from app.contracts.transformer_contract import TransformerContract
from app.schemas.constants.conversations import ConversationStatus, MessageAuthor
from app.schemas.domain.bookings import LeadDocument
from app.schemas.domain.conversations import ConversationDocument, MessageDocument
from app.schemas.domain.handoffs import HandoffDocument
from app.schemas.dto.inbox.inbox_views import (
    InboxHandoffSummary,
    InboxItemSource,
    InboxItemView,
    InboxRequestSummary,
)
from app.utilities.conversations.message_previews import (
    build_written_message_preview,
    first_attachment_kind,
)


class InboxItemTransformer(TransformerContract[InboxItemSource, InboxItemView]):
    """
    The staff-safe row of a conversation in the team inbox: contact,
    channel, status, the team fields, the beginning of the last message
    someone wrote (system notes are not previews), the note count and the
    open work (handoff reason and urgency; request type, status, date and
    party size, never its free-text details).
    """

    def transform(self, input_data: InboxItemSource) -> InboxItemView:
        conversation: ConversationDocument = input_data.conversation
        last_message: MessageDocument | None = input_data.last_written
        if last_message is not None and last_message.author is MessageAuthor.SYSTEM:
            last_message = None

        return InboxItemView(
            id=conversation.id,
            contact_id=conversation.contact_id,
            contact_name=None
            if input_data.contact is None
            else input_data.contact.name,
            contact_phone_number=(
                None if input_data.contact is None else input_data.contact.phone_number
            ),
            channel=conversation.channel,
            language=conversation.language,
            status=conversation.status,
            is_after_hours=conversation.is_after_hours,
            needs_person=conversation.status is ConversationStatus.HANDOFF,
            has_open_request=conversation.has_open_request,
            awaits_team=conversation.awaits_team,
            assignee_user_id=conversation.assignee_user_id,
            assigned_at=conversation.assigned_at,
            is_assigned_automatically=(
                conversation.assignee_user_id is not None
                and conversation.assigned_by is None
            ),
            assignment_revision=conversation.assignment_revision,
            last_message_text=(
                None
                if last_message is None
                else build_written_message_preview(last_message)
            ),
            last_message_attachment=(
                None if last_message is None else first_attachment_kind(last_message)
            ),
            last_message_author=None if last_message is None else last_message.author,
            last_message_at=conversation.last_message_at,
            created_at=conversation.created_at,
            note_count=input_data.note_count,
            handoff=summarize_handoff(input_data.handoff),
            request=summarize_request(input_data.request),
            acquisition_source=conversation.acquisition_source,
        )


def summarize_handoff(handoff: HandoffDocument | None) -> InboxHandoffSummary | None:
    if handoff is None:
        return None

    return InboxHandoffSummary(
        id=handoff.id,
        reason=handoff.reason,
        urgency=handoff.urgency,
        status=handoff.status,
        created_at=handoff.created_at,
    )


def summarize_request(lead: LeadDocument | None) -> InboxRequestSummary | None:
    if lead is None:
        return None

    return InboxRequestSummary(
        id=lead.id,
        lead_type=lead.lead_type,
        status=lead.status,
        requested_date=lead.requested_date,
        party_size=lead.party_size,
        created_at=lead.created_at,
    )
