"""Sending staff messages through a business's own channels."""

import json

import pytest
from typed_time_provider import Microseconds

from app.schemas.constants.billing import UsageKind
from app.schemas.constants.channels import ChannelKind, ChannelStatus
from app.schemas.exceptions.application_errors import ExternalServiceError
from app.schemas.typings.channels.constrained_strings import (
    WhatsAppTemplateLanguageCode,
    WhatsAppTemplateName,
)
from app.schemas.typings.channels.strings import EncryptedChannelSecret
from app.schemas.typings.conversations.strings import ChannelUserId, MessageText
from app.schemas.typings.localization.constrained_strings import LanguageTag
from tests.channels.channels_payloads import telegram_ok
from tests.channels.channels_settings import PAGE_ACCESS_TOKEN, TELEGRAM_BOT_TOKEN
from tests.channels.testbed import ChannelsTestbed


class TestChannelMessageSender:
    def test_proactive_message_through_each_connected_messenger(self) -> None:
        testbed = ChannelsTestbed()
        owner = testbed.add_user("owner")
        business = testbed.add_business(owner)
        testbed.add_channel(
            business.id, ChannelKind.TELEGRAM, "bot_name", TELEGRAM_BOT_TOKEN
        )
        testbed.add_channel(business.id, ChannelKind.WHATSAPP, "106540352242922")
        testbed.add_channel(
            business.id, ChannelKind.INSTAGRAM, "1784", PAGE_ACCESS_TOKEN
        )
        testbed.telegram_transport.respond("POST", r"/sendMessage$", telegram_ok({}))
        testbed.meta_transport.respond("POST", r"/messages$", {"messages": []})
        sender = testbed.channel_message_sender
        text = MessageText("Your booking is confirmed.")

        sender.send(business.id, ChannelKind.TELEGRAM, ChannelUserId("42"), text)
        sender.send(
            business.id, ChannelKind.WHATSAPP, ChannelUserId("995599123456"), text
        )
        sender.send(business.id, ChannelKind.INSTAGRAM, ChannelUserId("igsid"), text)

        assert testbed.telegram_transport.requests[0].path == (
            f"/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
        )
        assert [request.path for request in testbed.meta_transport.requests] == [
            "/v23.0/106540352242922/messages",
            "/v23.0/me/messages",
        ]
        usage = testbed.usage_event_repo.list_by_business_between(
            business.id,
            testbed.clock.now_microseconds(),
            Microseconds(testbed.clock.now_microseconds() + 1),
        )
        assert [(event.kind, event.quantity) for event in usage] == [
            (UsageKind.WHATSAPP_REPLY, 1)
        ]

    def test_a_reminder_template_is_sent_from_the_business_number_once(
        self,
    ) -> None:
        testbed = ChannelsTestbed()
        owner = testbed.add_user("owner")
        business = testbed.add_business(owner)
        testbed.add_channel(business.id, ChannelKind.WHATSAPP, "106540352242922")
        testbed.meta_transport.respond("POST", r"/messages$", {"messages": []})

        testbed.channel_message_sender.send_whatsapp_template(
            business.id,
            ChannelUserId("995599123456"),
            WhatsAppTemplateName("booking_reminder"),
            LanguageTag("ka"),
            [
                MessageText("Salobie Bia"),
                MessageText("6 October"),
                MessageText("19:00"),
            ],
        )

        [request] = testbed.meta_transport.requests
        assert request.path == "/v23.0/106540352242922/messages"
        body = json.loads(request.body)
        assert body["type"] == "template"
        assert body["template"]["name"] == "booking_reminder"
        assert body["template"]["language"]["code"] == "ka"
        usage = testbed.usage_event_repo.list_by_business_between(
            business.id,
            testbed.clock.now_microseconds(),
            Microseconds(testbed.clock.now_microseconds() + 1),
        )
        assert [(event.kind, event.quantity) for event in usage] == [
            (UsageKind.WHATSAPP_TEMPLATE, 1)
        ]

    def test_a_staff_template_goes_in_its_own_language_without_fallback(
        self,
    ) -> None:
        testbed = ChannelsTestbed()
        owner = testbed.add_user("owner")
        business = testbed.add_business(owner)
        testbed.add_channel(business.id, ChannelKind.WHATSAPP, "106540352242922")
        testbed.meta_transport.respond("POST", r"/messages$", {"messages": []})
        sender = testbed.channel_message_sender

        sender.send_whatsapp_template_in_language(
            business.id,
            ChannelUserId("995599123456"),
            WhatsAppTemplateName("staff_reply"),
            WhatsAppTemplateLanguageCode("pt_BR"),
            [MessageText("Sua mesa está pronta.")],
        )
        testbed.meta_transport.respond(
            "POST",
            r"/messages$",
            {"error": {"message": "Template name does not exist", "code": 132001}},
            status_code=400,
        )
        with pytest.raises(ExternalServiceError):
            sender.send_whatsapp_template_in_language(
                business.id,
                ChannelUserId("995599123456"),
                WhatsAppTemplateName("staff_reply"),
                WhatsAppTemplateLanguageCode("pt_BR"),
                [MessageText("Again")],
            )

        sent, refused = testbed.meta_transport.requests
        body = json.loads(sent.body)
        assert body["template"]["name"] == "staff_reply"
        assert body["template"]["language"]["code"] == "pt_BR"
        assert body["template"]["components"][0]["parameters"] == [
            {"type": "text", "text": "Sua mesa está pronta."}
        ]
        assert json.loads(refused.body)["template"]["language"]["code"] == "pt_BR"
        usage = testbed.usage_event_repo.list_by_business_between(
            business.id,
            testbed.clock.now_microseconds(),
            Microseconds(testbed.clock.now_microseconds() + 1),
        )
        assert [(event.kind, event.quantity) for event in usage] == [
            (UsageKind.WHATSAPP_TEMPLATE, 1)
        ]

    def test_unsupported_or_missing_channels_raise(self) -> None:
        testbed = ChannelsTestbed()
        owner = testbed.add_user("owner")
        business = testbed.add_business(owner)
        testbed.add_channel(business.id, ChannelKind.PHONE, "+995322000000")
        testbed.add_channel(
            business.id,
            ChannelKind.MESSENGER,
            "4410001",
            PAGE_ACCESS_TOKEN,
            status=ChannelStatus.DISABLED,
        )
        other_owner = testbed.add_user("other")
        other = testbed.add_business(other_owner, name="Other")
        testbed.add_channel(
            other.id, ChannelKind.TELEGRAM, "other_bot", TELEGRAM_BOT_TOKEN
        )
        text = MessageText("Hello")
        sender = testbed.channel_message_sender

        for channel in (
            ChannelKind.PHONE,
            ChannelKind.WEB_CHAT,
            ChannelKind.MESSENGER,
            ChannelKind.TELEGRAM,
        ):
            with pytest.raises(ExternalServiceError):
                sender.send(business.id, channel, ChannelUserId("1"), text)

        assert testbed.telegram_transport.requests == []

    def test_unreadable_credentials_ask_to_reconnect(self) -> None:
        testbed = ChannelsTestbed()
        owner = testbed.add_user("owner")
        business = testbed.add_business(owner)
        channel = testbed.add_channel(business.id, ChannelKind.TELEGRAM, "bot", "token")
        channel.encrypted_secret = EncryptedChannelSecret("garbage")
        testbed.channel_repo.save(channel)

        with pytest.raises(ExternalServiceError, match="reconnect"):
            testbed.channel_message_sender.send(
                business.id, ChannelKind.TELEGRAM, ChannelUserId("1"), MessageText("Hi")
            )
