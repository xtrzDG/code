"""Staff notifications go through the outbox: queued, sent by the worker, tracked."""

import json
import logging

import httpx
import pytest

from app.adapters.channels.whatsapp_channel_adapter import WhatsAppChannelAdapter
from app.clients.meta.meta_graph_client import MetaGraphClient
from app.facilitators.notifications.staff_notification_sender_facilitator import (
    StaffNotificationSenderFacilitator,
)
from app.schemas.constants.deliveries import OutboundMessageStatus
from app.schemas.constants.handoffs import ManagerContactChannel
from app.schemas.domain.businesses import ManagerContact
from app.schemas.domain.outbound_messages import OutboundTemplate
from app.schemas.dto.deliveries import StaffNotification
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.channels.constrained_strings import (
    WhatsAppTemplateLanguageCode,
    WhatsAppTemplateName,
)
from app.schemas.typings.conversations.strings import MessageText
from app.schemas.typings.handoffs.strings import ManagerContactAddress, ManagerName
from app.schemas.typings.localization.constrained_strings import LanguageTag
from tests.channels.channels_payloads import telegram_ok
from tests.channels.channels_settings import PLATFORM_BOT_TOKEN, build_settings
from tests.channels.outbox_reads import outbox_of
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


def notify(testbed: ChannelsTestbed, to: ManagerContact) -> bool:
    return testbed.staff_notifier.notify(
        StaffNotification(business_id=BUSINESS_ID, contact=to, text=HANDOFF_TEXT)
    )


BUSINESS_ID: BusinessId = BusinessId()


class TestManagerNotifications:
    def test_telegram_is_queued_then_sent_through_the_platform_bot(self) -> None:
        testbed = ChannelsTestbed()
        testbed.telegram_transport.respond(
            "POST", r"/sendMessage$", telegram_ok({"message_id": 7})
        )

        assert notify(testbed, contact(ManagerContactChannel.TELEGRAM, "-100555"))
        assert testbed.telegram_transport.requests == []
        [queued] = outbox_of(testbed, BUSINESS_ID)
        assert queued.status is OutboundMessageStatus.PENDING

        testbed.run_worker()

        [request] = testbed.telegram_transport.requests
        assert request.path == f"/bot{PLATFORM_BOT_TOKEN}/sendMessage"
        assert request.json()["chat_id"] == "-100555"
        assert request.json()["text"] == str(HANDOFF_TEXT)
        [delivered] = outbox_of(testbed, BUSINESS_ID)
        assert delivered.status is OutboundMessageStatus.DELIVERED
        assert delivered.provider_message_id == "-100555:7"
        assert delivered.delivered_at == testbed.clock.now_microseconds()

    @pytest.mark.parametrize(
        ("language", "template_language"),
        [("pt-BR", "pt_BR"), ("ka", "ka"), ("he", "he"), ("kk", "kk")],
    )
    def test_whatsapp_template_in_the_staff_language(
        self, language: str, template_language: str
    ) -> None:
        testbed = ChannelsTestbed()
        testbed.meta_transport.respond(
            "POST", r"/messages$", {"messages": [{"id": "wamid.1"}]}
        )

        assert notify(
            testbed,
            contact(ManagerContactChannel.WHATSAPP, "+5511961234567", language),
        )
        testbed.run_worker()

        [request] = testbed.meta_transport.requests
        assert request.path == "/v23.0/900000000000001/messages"
        body = request.json()
        assert body["to"] == "5511961234567"
        assert body["template"]["name"] == "staff_notification"
        assert body["template"]["language"] == {"code": template_language}
        assert body["template"]["components"][0]["parameters"] == [
            {"type": "text", "text": str(HANDOFF_TEXT)}
        ]
        [delivered] = outbox_of(testbed, BUSINESS_ID)
        assert delivered.provider_message_id == "wamid.1"

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
        sender = StaffNotificationSenderFacilitator(
            testbed.telegram_client, adapter, testbed.settings
        )

        sender.send(
            contact(ManagerContactChannel.WHATSAPP, "+995599123456", "ka"),
            HANDOFF_TEXT,
            OutboundTemplate(
                name=WhatsAppTemplateName("staff_notification"),
                language_code=WhatsAppTemplateLanguageCode("ka"),
            ),
        )
        assert calls == ["ka", "en"]

    def test_temporary_failures_are_retried_and_refusals_are_dead(self) -> None:
        testbed = ChannelsTestbed()
        testbed.telegram_transport.failure = httpx.ConnectError("down")
        testbed.meta_transport.respond(
            "POST",
            r"/messages$",
            {"error": {"message": "template missing", "code": 132001}},
            status_code=400,
        )

        assert notify(testbed, contact(ManagerContactChannel.TELEGRAM, "1"))
        assert notify(
            testbed, contact(ManagerContactChannel.WHATSAPP, "+995599123456", "en")
        )
        testbed.run_worker()

        by_channel = {
            message.staff_contact.channel: message
            for message in outbox_of(testbed, BUSINESS_ID)
            if message.staff_contact is not None
        }
        telegram = by_channel[ManagerContactChannel.TELEGRAM]
        assert telegram.status is OutboundMessageStatus.PENDING
        assert telegram.attempts == 1
        assert telegram.next_attempt_at == testbed.clock.now_microseconds() + 10_000_000
        assert "ConnectError" in str(telegram.last_error)
        whatsapp = by_channel[ManagerContactChannel.WHATSAPP]
        assert whatsapp.status is OutboundMessageStatus.DEAD
        assert "132001" in str(whatsapp.last_error)

        # The platform bot comes back: the retry delivers the notification.
        testbed.telegram_transport.failure = None
        testbed.telegram_transport.respond("POST", r"/sendMessage$", telegram_ok({}))
        testbed.clock.advance(10)
        testbed.run_worker()
        [retried] = [
            message
            for message in outbox_of(testbed, BUSINESS_ID)
            if message.id == telegram.id
        ]
        assert retried.status is OutboundMessageStatus.DELIVERED
        assert retried.attempts == 2

    def test_missing_configuration_is_dead_at_once(self) -> None:
        unconfigured = ChannelsTestbed(
            build_settings(
                TELEGRAM_PLATFORM_BOT_TOKEN="",
                WHATSAPP_NOTIFICATION_TEMPLATE="",
            )
        )

        assert not notify(unconfigured, contact(ManagerContactChannel.TELEGRAM, "1"))
        assert not notify(
            unconfigured, contact(ManagerContactChannel.WHATSAPP, "+995599123456")
        )
        unconfigured.run_worker()

        assert unconfigured.telegram_transport.requests == []
        assert unconfigured.meta_transport.requests == []
        reasons = sorted(
            str(message.last_error) for message in outbox_of(unconfigured, BUSINESS_ID)
        )
        assert reasons == [
            "TELEGRAM_PLATFORM_BOT_TOKEN is not configured.",
            "WHATSAPP_NOTIFICATION_PHONE_NUMBER_ID or WHATSAPP_NOTIFICATION_TEMPLATE "
            "is not configured.",
        ]

    def test_email_and_sms_without_a_provider(
        self, caplog: pytest.LogCaptureFixture
    ) -> None:
        development = ChannelsTestbed()
        production = ChannelsTestbed(build_settings(APP_ENV="production"))
        email = contact(ManagerContactChannel.EMAIL, "levan@example.ge")
        sms = contact(ManagerContactChannel.SMS, "+995599123456")

        with caplog.at_level(logging.INFO):
            assert notify(development, email) is True
            assert notify(development, sms) is True
            development.run_worker()
            assert notify(production, email) is False
            assert notify(production, sms) is False

        assert {message.status for message in outbox_of(development, BUSINESS_ID)} == {
            OutboundMessageStatus.DELIVERED
        }
        assert str(HANDOFF_TEXT) not in caplog.text
        assert "levan@example.ge" not in caplog.text
        assert "***.ge" in caplog.text
