from app.contracts.transformer_contract import TransformerContract
from app.schemas.constants.conversations import MessageAuthor
from app.schemas.domain.conversations import ConversationDocument, MessageDocument
from app.schemas.dto.conversation_feed.conversation_views import (
    ConversationSummaryView,
    ConversationViewSource,
)
from app.utilities.conversations.message_previews import (
    build_written_message_preview,
    first_attachment_kind,
)


class ConversationSummaryTransformer(
    TransformerContract[ConversationViewSource, ConversationSummaryView]
):
    """
    A conversation row of the feed: contact, channel, status, flags, how
    many messages (all and the customer's) and the beginning of the last
    message someone wrote. System notes (the voice agent's "Voice agent
    called check_availability.") are not previews: a phone conversation
    shows no message line rather than an English technical note.
    """

    def transform(self, input_data: ConversationViewSource) -> ConversationSummaryView:
        conversation: ConversationDocument = input_data.conversation
        last_message: MessageDocument | None = input_data.last_written
        if last_message is not None and last_message.author is MessageAuthor.SYSTEM:
            last_message = None
        return ConversationSummaryView(
            id=conversation.id,
            business_id=conversation.business_id,
            contact_id=conversation.contact_id,
            contact_name=None
            if input_data.contact is None
            else input_data.contact.name,
            contact_phone_number=(
                None if input_data.contact is None else input_data.contact.phone_number
            ),
            assistant_version_id=conversation.assistant_version_id,
            channel=conversation.channel,
            language=conversation.language,
            status=conversation.status,
            is_after_hours=conversation.is_after_hours,
            is_sandbox=conversation.is_sandbox,
            message_count=input_data.tally.message_count,
            customer_message_count=input_data.tally.customer_message_count,
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
            rating=conversation.rating,
            rating_reason=conversation.rating_reason,
            rated_message_id=conversation.rated_message_id,
        )
