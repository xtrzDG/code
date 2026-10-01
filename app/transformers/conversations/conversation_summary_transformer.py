from app.contracts.transformer_contract import TransformerContract
from app.schemas.constants.conversations import MessageAuthor
from app.schemas.domain.conversations import ConversationDocument, MessageDocument
from app.schemas.dto.conversation_feed import (
    ConversationSummaryView,
    ConversationViewSource,
)
from app.schemas.typings.conversations.constrained_integers import (
    ConversationMessageCount,
)
from app.utilities.conversations.message_previews import build_message_preview


class ConversationSummaryTransformer(
    TransformerContract[ConversationViewSource, ConversationSummaryView]
):
    """
    A conversation row of the feed: contact, channel, status, flags, how
    many messages (all and the customer's) and the beginning of the last one.
    """

    def transform(self, input_data: ConversationViewSource) -> ConversationSummaryView:
        conversation: ConversationDocument = input_data.conversation
        last_message: MessageDocument | None = (
            input_data.messages[-1] if input_data.messages else None
        )
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
            message_count=ConversationMessageCount(len(input_data.messages)),
            customer_message_count=ConversationMessageCount(
                sum(
                    1
                    for message in input_data.messages
                    if message.author is MessageAuthor.CUSTOMER
                )
            ),
            last_message_text=(
                None
                if last_message is None
                else build_message_preview(last_message.text)
            ),
            last_message_author=None if last_message is None else last_message.author,
            last_message_at=conversation.last_message_at,
            created_at=conversation.created_at,
            rating=conversation.rating,
        )
