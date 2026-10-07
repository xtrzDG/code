"""The widget reads the options of an assistant reply with the reply."""

from app.schemas.constants.channels import MessageDirection
from app.schemas.constants.conversations import MessageAuthor
from app.schemas.domain.conversations import MessageDocument
from app.schemas.domain.reply_choices import ReplyChoices
from app.schemas.typings.conversations.constrained_strings import (
    ChoiceLabel,
    ChoicePromptText,
)
from app.schemas.typings.conversations.prefixed_id import ConversationId
from app.schemas.typings.conversations.strings import MessageText
from app.schemas.typings.localization.constrained_strings import LanguageTag
from tests.channels.test_widget import enable_widget
from tests.channels.testbed import ChannelsTestbed
from tests.channels.widget_polling_steps import poll, send


def test_an_assistant_reply_comes_with_its_options() -> None:
    testbed = ChannelsTestbed()
    business = enable_widget(testbed)
    client = testbed.build_http_client()
    reply = send(testbed, business.id, "A table tonight?")
    testbed.clock.advance(5)
    now = testbed.clock.now_microseconds()
    offer = MessageDocument(
        conversation_id=ConversationId(reply["conversation_id"]),
        business_id=business.id,
        direction=MessageDirection.OUTBOUND,
        author=MessageAuthor.ASSISTANT,
        text=MessageText("We have a table.\n\nWhich time suits you?"),
        language=LanguageTag("en"),
        choices=ReplyChoices(
            prompt=ChoicePromptText("Which time suits you?"),
            options=[ChoiceLabel("18:00"), ChoiceLabel("19:30")],
            language=LanguageTag("en"),
        ),
        created_at=now,
        updated_at=now,
    )
    testbed.message_repo.save(offer)

    items = poll(client, business.id, after=reply["message_id"]).json()["items"]

    assert [(item["text"], item["choices"]) for item in items] == [
        ("We have a table.\n\nWhich time suits you?", ["18:00", "19:30"])
    ]
