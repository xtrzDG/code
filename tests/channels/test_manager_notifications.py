"""Notifying managers of handoffs through the platform's channels."""

import json
import logging

import httpx
import pytest

from app.adapters.channels.whatsapp_channel_adapter import WhatsAppChannelAdapter
from app.clients.meta.meta_graph_client import MetaGraphClient
from app.facilitators.notifications.manager_notification_facilitator import (
    ManagerNotificationFacilitator,
)
from app.schemas.constants.handoffs import ManagerContactChannel
from app.schemas.domain.businesses import ManagerContact
from app.schemas.typings.conversations.strings import MessageText
from app.schemas.typings.handoffs.strings import ManagerContactAddress, ManagerName
from app.schemas.typings.localization.constrained_strings import LanguageTag
from tests.channels.channels_payloads import telegram_ok
from tests.channels.channels_settings import PLATFORM_BOT_TOKEN, build_settings
from tests.channels.testbed import ChannelsTestbed

HANDOFF_TEXT = MessageText("Handoff: guest asks about a banquet for 40 people.")


def contact(
    channel: ManagerContactChannel,
    address: str,
    language: str = "ru",
) -> ManagerContact:
    return ManagerContact(
        name=ManagerName("Levan"),
        channel=channel,
        address=ManagerContactAddress(address),
        language=LanguageTag(language),
    )


def build_facilitator(testbed: ChannelsTestbed) -> ManagerNotificationFacilitator:
    return ManagerNotificationFacilitator(
        testbed.telegram_client, testbed.whatsapp_adapter, testbed.settings
    )


class TestManagerNotifications:
    def test_telegram_through_the_platform_bot(self) -> None:
        testbed = ChannelsTestbed()
        testbed.telegram_transport.respond("POST", r"/sendMessage$", telegram_ok({}))

        delivered = build_facilitator(testbed).notify(
            contact(ManagerContactChannel.TELEGRAM, "-100555"), HANDOFF_TEXT
        )

        assert delivered is True
        [request] = testbed.telegram_transport.requests
        assert request.path == f"/bot{PLATFORM_BOT_TOKEN}/sendMessage"
        assert request.json()["chat_id"] == "-100555"
        assert request.json()["text"] == str(HANDOFF_TEXT)

    @pytest.mark.parametrize(
        ("language", "template_language"),
        [("pt-BR", "pt_BR"), ("ka", "ka"), ("he", "he"), ("kk", "kk")],
    )
    def test_whatsapp_template_in_the_staff_language(
        self, language: str, template_language: str
    ) -> None:
        testbed = ChannelsTestbed()
        testbed.meta_transport.respond("POST", r"/messages$", {"messages": []})

        delivered = build_facilitator(testbed).notify(
            contact(ManagerContactChannel.WHATSAPP, "+5511961234567", language),
            HANDOFF_TEXT,
        )

        assert delivered is True
        [request] = testbed.meta_transport.requests
        assert request.path == "/v23.0/900000000000001/messages"
        body = request.json()
        assert body["to"] == "5511961234567"
        assert body["template"]["name"] == "staff_notification"
        assert body["template"]["language"] == {"code": template_language}
        assert body["template"]["components"][0]["parameters"] == [
            {"type": "text", "text": str(HANDOFF_TEXT)}
        ]

    def test_whatsapp_falls_back_to_the_english_template(self) -> None:
        testbed = ChannelsTestbed()
        calls: list[str] = []

        def handle(request: httpx.Request) -> httpx.Response:
            code: str = json.loads(request.content)["template"]["language"]["code"]
            calls.append(code)
            if code == "en":
                return httpx.Response(200, json={"messages": []})
            return httpx.Response(
                400, json={"error": {"message": "template missing", "code": 132001}}
            )

        adapter = WhatsAppChannelAdapter(
            MetaGraphClient(transport=httpx.MockTransport(handle)),
            testbed.phone_number_parser,
            testbed.settings,
        )
        facilitator = ManagerNotificationFacilitator(
            testbed.telegram_client, adapter, testbed.settings
        )

        assert facilitator.notify(
            contact(ManagerContactChannel.WHATSAPP, "+995599123456", "ka"), HANDOFF_TEXT
        )
        assert calls == ["ka", "en"]

    def test_failures_and_missing_configuration_return_false(
        self, caplog: pytest.LogCaptureFixture
    ) -> None:
        testbed = ChannelsTestbed()
        testbed.telegram_transport.failure = httpx.ConnectError("down")
        testbed.meta_transport.respond(
            "POST",
            r"/messages$",
            {"error": {"message": "template missing", "code": 132001}},
            status_code=400,
        )
        facilitator = build_facilitator(testbed)

        with caplog.at_level(logging.WARNING):
            assert not facilitator.notify(
                contact(ManagerContactChannel.TELEGRAM, "1"), HANDOFF_TEXT
            )
            assert not facilitator.notify(
                contact(ManagerContactChannel.WHATSAPP, "+995599123456", "en"),
                HANDOFF_TEXT,
            )

        unconfigured = ChannelsTestbed(
            build_settings(
                TELEGRAM_PLATFORM_BOT_TOKEN="",
                WHATSAPP_NOTIFICATION_TEMPLATE="",
            )
        )
        quiet = build_facilitator(unconfigured)
        assert not quiet.notify(
            contact(ManagerContactChannel.TELEGRAM, "1"), HANDOFF_TEXT
        )
        assert not quiet.notify(
            contact(ManagerContactChannel.WHATSAPP, "+995599123456"), HANDOFF_TEXT
        )
        assert unconfigured.telegram_transport.requests == []
        assert unconfigured.meta_transport.requests == []

    def test_email_and_sms_without_a_provider(
        self, caplog: pytest.LogCaptureFixture
    ) -> None:
        development = build_facilitator(ChannelsTestbed())
        production = build_facilitator(
            ChannelsTestbed(build_settings(APP_ENV="production"))
        )
        email = contact(ManagerContactChannel.EMAIL, "levan@example.ge")
        sms = contact(ManagerContactChannel.SMS, "+995599123456")

        with caplog.at_level(logging.INFO):
            assert development.notify(email, HANDOFF_TEXT) is True
            assert development.notify(sms, HANDOFF_TEXT) is True
            assert production.notify(email, HANDOFF_TEXT) is False
            assert production.notify(sms, HANDOFF_TEXT) is False

        assert str(HANDOFF_TEXT) not in caplog.text
        assert "levan@example.ge" not in caplog.text
        assert "***.ge" in caplog.text
