"""The feed row previews what someone wrote, not the voice agent's notes."""

from typed_time_provider import Microseconds

from app.schemas.constants.channels import ChannelKind, MessageDirection
from app.schemas.constants.conversations import MessageAuthor
from app.schemas.domain.conversations import ConversationDocument, MessageDocument
from app.schemas.dto.conversation_feed.conversation_views import ConversationViewSource
from app.schemas.dto.conversation_feed.message_tallies import ConversationMessageTally
from app.schemas.typings.assistants.prefixed_id import AssistantVersionId
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.contacts.prefixed_id import ContactId
from app.schemas.typings.conversations.constrained_integers import (
    ConversationMessageCount,
)
from app.schemas.typings.conversations.strings import ChannelUserId, MessageText
from app.transformers.conversations.conversation_summary_transformer import (
    ConversationSummaryTransformer,
)

BUSINESS_ID = BusinessId()


def conversation(channel: ChannelKind) -> ConversationDocument:
    return ConversationDocument(
        business_id=BUSINESS_ID,
        contact_id=ContactId(),
        assistant_version_id=AssistantVersionId(),
        channel=channel,
        channel_user_id=ChannelUserId("conv_0001"),
        last_message_at=Microseconds(1_000_000),
    )


def message(
    owner: ConversationDocument, author: MessageAuthor, text: str
) -> MessageDocument:
    return MessageDocument(
        conversation_id=owner.id,
        business_id=BUSINESS_ID,
        direction=(
            MessageDirection.INBOUND
            if author is MessageAuthor.CUSTOMER
            else MessageDirection.OUTBOUND
        ),
        author=author,
        text=MessageText(text),
    )


def test_a_phone_conversation_with_only_voice_agent_notes_has_no_preview() -> None:
    call = conversation(ChannelKind.PHONE)
    note = message(call, MessageAuthor.SYSTEM, "Voice agent called create_booking.")

    row = ConversationSummaryTransformer().transform(
        ConversationViewSource(
            conversation=call,
            tally=ConversationMessageTally(message_count=ConversationMessageCount(2)),
            last_written=note,
        )
    )

    assert (row.last_message_text, row.last_message_author) == (None, None)
    assert int(row.message_count) == 2


def test_the_preview_is_the_last_message_someone_wrote() -> None:
    chat = conversation(ChannelKind.TELEGRAM)
    reply = message(chat, MessageAuthor.ASSISTANT, "Да, в 20:00.")

    row = ConversationSummaryTransformer().transform(
        ConversationViewSource(
            conversation=chat,
            tally=ConversationMessageTally(
                message_count=ConversationMessageCount(3),
                customer_message_count=ConversationMessageCount(1),
            ),
            last_written=reply,
        )
    )

    assert str(row.last_message_text) == "Да, в 20:00."
    assert row.last_message_author is MessageAuthor.ASSISTANT
    assert (int(row.message_count), int(row.customer_message_count)) == (3, 1)
