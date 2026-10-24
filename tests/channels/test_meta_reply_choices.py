"""
A reply that offers options in Meta's channels: WhatsApp reply buttons (up
to three) or a list behind one button, Messenger and Instagram quick
replies, and the numbered list when the platform refuses them.
"""

from typing import Any

from app.schemas.constants.channels import ChannelKind
from app.schemas.constants.deliveries import OutboundMessageKind
from app.schemas.domain.reply_choices import ReplyChoices
from app.schemas.dto.channels.channel_webhooks import ChannelDeliveryTarget
from app.schemas.typings.channels.strings import ChannelExternalId, ChannelSecret
from app.schemas.typings.conversations.constrained_strings import (
    ChoiceLabel,
    ChoicePromptText,
)
from app.schemas.typings.conversations.strings import ChannelUserId, MessageText
from app.schemas.typings.localization.constrained_strings import LanguageTag
from tests.channels.channels_settings import PAGE_ACCESS_TOKEN
from tests.channels.customer_outbox import queue_customer_message
from tests.channels.meta_payloads import INSTAGRAM_ID, PAGE_ID, PHONE_NUMBER_ID
from tests.channels.testbed import ChannelsTestbed
from tests.contracts.vendor_schemas import assert_outbound

WHATSAPP_SPEC: str = "meta_whatsapp_cloud_api.json"
PAGES_SPEC: str = "meta_messenger_platform.json"
CUSTOMER: str = "995599123456"
SENT: dict[str, object] = {"messages": [{"id": "wamid.sent"}]}
REFUSED: dict[str, object] = {
    "error": {
        "message": "(#131009) Parameter value is not valid",
        "type": "OAuthException",
        "code": 131009,
    }
}


def choices(*options: str, language: str = "en") -> ReplyChoices:
    return ReplyChoices(
        prompt=ChoicePromptText("Which time suits you?"),
        options=[ChoiceLabel(option) for option in options],
        language=LanguageTag(language),
    )


def whatsapp_target() -> ChannelDeliveryTarget:
    return ChannelDeliveryTarget(
        channel=ChannelKind.WHATSAPP,
        account_id=ChannelExternalId(PHONE_NUMBER_ID),
        channel_user_id=ChannelUserId(CUSTOMER),
    )


def page_target(kind: ChannelKind, account_id: str) -> ChannelDeliveryTarget:
    return ChannelDeliveryTarget(
        channel=kind,
        account_id=ChannelExternalId(account_id),
        channel_user_id=ChannelUserId("psid-1"),
        credential=ChannelSecret(PAGE_ACCESS_TOKEN),
    )


def sent_bodies(testbed: ChannelsTestbed) -> list[dict[str, Any]]:
    return [request.json() for request in testbed.meta_transport.requests]


class TestWhatsApp:
    def test_up_to_three_options_are_reply_buttons(self) -> None:
        testbed = ChannelsTestbed()
        testbed.meta_transport.respond("POST", r"/messages$", SENT)

        testbed.whatsapp_adapter.send(
            whatsapp_target(),
            MessageText("We have a table.\n\nWhich time suits you?"),
            choices("18:00", "19:30", "21:00"),
        )

        [body] = sent_bodies(testbed)
        assert body["type"] == "interactive"
        assert body["interactive"] == {
            "type": "button",
            "body": {"text": "We have a table.\n\nWhich time suits you?"},
            "action": {
                "buttons": [
                    {"type": "reply", "reply": {"id": "choice-1", "title": "18:00"}},
                    {"type": "reply", "reply": {"id": "choice-2", "title": "19:30"}},
                    {"type": "reply", "reply": {"id": "choice-3", "title": "21:00"}},
                ]
            },
        }
        assert_outbound(body, WHATSAPP_SPEC, "request:messages.send")

    def test_more_options_are_a_list_behind_a_button_in_the_reply_language(
        self,
    ) -> None:
        testbed = ChannelsTestbed()
        testbed.meta_transport.respond("POST", r"/messages$", SENT)

        testbed.whatsapp_adapter.send(
            whatsapp_target(),
            MessageText("Какое время вам удобно?"),
            choices("12:00", "13:00", "14:00", "15:00", "16:00", language="ru"),
        )

        [body] = sent_bodies(testbed)
        interactive = body["interactive"]
        assert interactive["type"] == "list"
        assert interactive["action"]["button"] == "Выбрать"
        rows = interactive["action"]["sections"][0]["rows"]
        assert [row["title"] for row in rows] == [
            "12:00",
            "13:00",
            "14:00",
            "15:00",
            "16:00",
        ]
        assert_outbound(body, WHATSAPP_SPEC, "request:messages.send")

    def test_refused_buttons_are_sent_again_as_a_numbered_list(self) -> None:
        testbed = ChannelsTestbed()
        testbed.meta_transport.respond_in_turn(
            "POST", r"/messages$", [(400, REFUSED), (200, SENT)]
        )

        receipt = testbed.whatsapp_adapter.send(
            whatsapp_target(),
            MessageText("Which time suits you?"),
            choices("18:00", "19:30"),
        )

        buttons, text = sent_bodies(testbed)
        assert buttons["type"] == "interactive"
        assert text["type"] == "text"
        assert text["text"]["body"] == "Which time suits you?\n\n1. 18:00\n2. 19:30"
        assert receipt.delivered == 1

    def test_a_long_reply_keeps_the_buttons_for_its_last_part(self) -> None:
        testbed = ChannelsTestbed()
        testbed.meta_transport.respond("POST", r"/messages$", SENT)
        long_text = ("Our menu and prices. " * 80).strip()

        receipt = testbed.whatsapp_adapter.send(
            whatsapp_target(), MessageText(long_text), choices("Yes", "No")
        )

        bodies = sent_bodies(testbed)
        assert receipt.delivered == len(bodies) > 1
        assert [body["type"] for body in bodies] == ["text"] * (len(bodies) - 1) + [
            "interactive"
        ]
        # A message with reply buttons carries at most 1024 characters.
        assert len(bodies[-1]["interactive"]["body"]["text"]) <= 1024

    def test_the_outbox_sends_the_reply_with_its_options(self) -> None:
        testbed = ChannelsTestbed()
        testbed.meta_transport.respond("POST", r"/messages$", SENT)
        owner_id = testbed.add_user("owner")
        business = testbed.add_business(owner_id)
        channel = testbed.add_channel(
            business.id, ChannelKind.WHATSAPP, PHONE_NUMBER_ID
        )
        queue_customer_message(
            testbed,
            channel,
            CUSTOMER,
            OutboundMessageKind.CUSTOMER_REPLY,
            text="Which time suits you?",
            choices=choices("18:00", "19:30"),
        )

        testbed.run_worker()

        [body] = sent_bodies(testbed)
        assert body["interactive"]["type"] == "button"


class TestPages:
    def test_messenger_and_instagram_offer_quick_replies(self) -> None:
        testbed = ChannelsTestbed()
        testbed.meta_transport.respond("POST", r"/me/messages$", {"message_id": "m"})
        offer = choices("18:00", "19:30")

        testbed.messenger_adapter.send(
            page_target(ChannelKind.MESSENGER, PAGE_ID),
            MessageText("Which time suits you?"),
            offer,
        )
        testbed.instagram_adapter.send(
            page_target(ChannelKind.INSTAGRAM, INSTAGRAM_ID),
            MessageText("Which time suits you?"),
            offer,
        )

        for body in sent_bodies(testbed):
            assert body["message"] == {
                "text": "Which time suits you?",
                "quick_replies": [
                    {"content_type": "text", "title": "18:00", "payload": "choice-1"},
                    {"content_type": "text", "title": "19:30", "payload": "choice-2"},
                ],
            }
            assert_outbound(body, PAGES_SPEC, "request:messages.send")

    def test_only_the_last_part_carries_quick_replies(self) -> None:
        testbed = ChannelsTestbed()
        testbed.meta_transport.respond("POST", r"/me/messages$", {"message_id": "m"})

        testbed.instagram_adapter.send(
            page_target(ChannelKind.INSTAGRAM, INSTAGRAM_ID),
            MessageText("Ok. " * 400),
            choices("Yes", "No"),
        )

        bodies = sent_bodies(testbed)
        assert len(bodies) == 2
        assert "quick_replies" not in bodies[0]["message"]
        assert len(bodies[1]["message"]["quick_replies"]) == 2

    def test_refused_quick_replies_become_a_numbered_list(self) -> None:
        testbed = ChannelsTestbed()
        testbed.meta_transport.respond_in_turn(
            "POST",
            r"/me/messages$",
            [(400, REFUSED), (200, {"message_id": "m"})],
        )

        testbed.messenger_adapter.send(
            page_target(ChannelKind.MESSENGER, PAGE_ID),
            MessageText("Which time suits you?"),
            choices("18:00", "19:30"),
        )

        _, numbered = sent_bodies(testbed)
        assert numbered["message"] == {
            "text": "Which time suits you?\n\n1. 18:00\n2. 19:30"
        }
