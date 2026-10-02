"""A channel whose platform refuses its credential turns ERROR and heals itself."""

import json

import pytest
from typed_time_provider import Microseconds

from app.adapters.channels.telegram_channel_adapter import TelegramChannelAdapter
from app.facilitators.channels.channel_message_sender_facilitator import (
    ChannelMessageSenderFacilitator,
)
from app.schemas.constants.billing import UsageKind
from app.schemas.constants.channels import ChannelKind, ChannelStatus
from app.schemas.domain.channels import ChannelDocument
from app.schemas.dto.channels.channel_webhooks import ChannelDeliveryTarget
from app.schemas.exceptions.application_errors import (
    ChannelCredentialRejectedError,
    ExternalServiceError,
)
from app.schemas.typings.channels.constrained_integers import DeliveredMessageCount
from app.schemas.typings.channels.constrained_strings import WhatsAppTemplateName
from app.schemas.typings.channels.strings import ChannelSecret
from app.schemas.typings.conversations.strings import ChannelUserId, MessageText
from app.schemas.typings.localization.constrained_strings import LanguageTag
from app.utilities.channels.channel_health import summarize_channel_error
from tests.channels.channels_payloads import bearer, telegram_ok
from tests.channels.channels_settings import (
    OTHER_TELEGRAM_BOT_TOKEN,
    PAGE_ACCESS_TOKEN,
    TELEGRAM_BOT_TOKEN,
)
from tests.channels.test_meta_channels import (
    PAGE_ID,
    page_message,
    page_webhook,
    post_meta,
)
from tests.channels.test_telegram_channel import build_update, connect_bot, post_update
from tests.channels.testbed import ChannelsTestbed

REVOKED: dict[str, object] = {
    "ok": False,
    "error_code": 401,
    "description": "Unauthorized",
}


def stored(testbed: ChannelsTestbed, channel: ChannelDocument) -> ChannelDocument:
    current = testbed.channel_repo.get(channel.id)
    assert current is not None
    return current


class TestTelegramChannelHealth:
    def test_revoked_bot_token_puts_the_channel_in_error_until_a_reply_works(
        self,
    ) -> None:
        testbed = ChannelsTestbed()
        business, channel = connect_bot(testbed)
        testbed.telegram_transport.respond(
            "POST", r"/sendMessage$", REVOKED, status_code=401
        )

        failed = post_update(testbed, channel, build_update())

        assert failed.status_code == 200
        assert failed.json()["failed"] == 1
        broken = stored(testbed, channel)
        assert broken.status is ChannelStatus.ERROR
        assert broken.last_error == (
            "Telegram sendMessage rejected the bot token (401: Unauthorized)."
        )
        assert broken.last_error_at == testbed.clock.now_microseconds()
        assert TELEGRAM_BOT_TOKEN not in str(broken.last_error)
        [view] = (
            testbed.build_http_client()
            .get(f"/v1/businesses/{business.id}/channels", headers=bearer("owner"))
            .json()
        )
        assert view["status"] == "error"
        assert view["last_error"] == str(broken.last_error)
        assert view["last_error_at"] == int(testbed.clock.now_microseconds())

        # The channel still receives messages; a delivered reply heals it.
        testbed.clock.advance(60)
        testbed.telegram_transport.respond("POST", r"/sendMessage$", telegram_ok({}))
        answered = post_update(testbed, channel, build_update(message_id=18))

        assert answered.json()["answered"] == 1
        healed = stored(testbed, channel)
        assert healed.status is ChannelStatus.CONNECTED
        assert healed.last_error is None
        assert healed.last_error_at is None

    def test_a_customer_who_blocked_the_bot_does_not_break_the_channel(self) -> None:
        testbed = ChannelsTestbed()
        _, channel = connect_bot(testbed)
        testbed.telegram_transport.respond(
            "POST",
            r"/sendMessage$",
            {"ok": False, "error_code": 403, "description": "Forbidden: blocked"},
            status_code=403,
        )

        post_update(testbed, channel, build_update())

        assert stored(testbed, channel).status is ChannelStatus.CONNECTED

    def test_proactive_messages_also_track_the_channel(self) -> None:
        testbed = ChannelsTestbed()
        business, channel = connect_bot(testbed)
        testbed.telegram_transport.respond(
            "POST", r"/sendMessage$", REVOKED, status_code=401
        )

        with pytest.raises(ChannelCredentialRejectedError):
            testbed.channel_message_sender.send(
                business.id,
                ChannelKind.TELEGRAM,
                ChannelUserId("555000111"),
                MessageText("See you at 19:00."),
            )

        assert stored(testbed, channel).status is ChannelStatus.ERROR
        testbed.telegram_transport.respond("POST", r"/sendMessage$", telegram_ok({}))
        testbed.channel_message_sender.send(
            business.id,
            ChannelKind.TELEGRAM,
            ChannelUserId("555000111"),
            MessageText("See you at 19:00."),
        )
        assert stored(testbed, channel).status is ChannelStatus.CONNECTED

    def test_reconnecting_clears_the_error(self) -> None:
        testbed = ChannelsTestbed()
        business, channel = connect_bot(testbed)
        broken = stored(testbed, channel)
        broken.status = ChannelStatus.ERROR
        broken.last_error = summarize_channel_error("Telegram rejected the token.")
        testbed.channel_repo.save(broken)
        testbed.telegram_transport.respond(
            "POST", r"/getMe$", telegram_ok({"username": "funicular_vr_bot"})
        )
        testbed.telegram_transport.respond("POST", r"/setWebhook$", telegram_ok(True))

        response = testbed.build_http_client().put(
            f"/v1/businesses/{business.id}/channels/telegram",
            json={"bot_token": TELEGRAM_BOT_TOKEN},
            headers=bearer("owner"),
        )

        assert response.status_code == 200, response.text
        assert response.json()["status"] == "connected"
        assert response.json()["last_error"] is None
        assert stored(testbed, channel).last_error_at is None

    def test_disabled_channels_are_not_marked(self) -> None:
        testbed = ChannelsTestbed()
        business, channel = connect_bot(testbed)
        disabled = stored(testbed, channel)
        disabled.status = ChannelStatus.DISABLED
        testbed.channel_repo.save(disabled)

        with pytest.raises(ExternalServiceError, match="not connected"):
            testbed.channel_message_sender.send(
                business.id,
                ChannelKind.TELEGRAM,
                ChannelUserId("555000111"),
                MessageText("Hello"),
            )

        assert stored(testbed, channel).status is ChannelStatus.DISABLED


class TestMetaChannelHealth:
    def test_expired_page_token_puts_messenger_in_error(self) -> None:
        testbed = ChannelsTestbed()
        owner = testbed.add_user("owner")
        business = testbed.add_business(owner)
        channel = testbed.add_channel(
            business.id, ChannelKind.MESSENGER, PAGE_ID, PAGE_ACCESS_TOKEN
        )
        testbed.meta_transport.respond(
            "POST",
            r"/me/messages$",
            {
                "error": {
                    "message": "Error validating access token: Session has expired.",
                    "type": "OAuthException",
                    "code": 190,
                }
            },
            status_code=400,
        )

        post_meta(
            testbed,
            page_webhook("page", PAGE_ID, [page_message("ps-1", "Hi", PAGE_ID)]),
        )

        broken = stored(testbed, channel)
        assert broken.status is ChannelStatus.ERROR
        assert "(190)" in str(broken.last_error)
        assert "Session has expired" in str(broken.last_error)
        assert PAGE_ACCESS_TOKEN not in str(broken.last_error)

        testbed.meta_transport.respond("POST", r"/me/messages$", {"message_id": "m"})
        post_meta(
            testbed,
            page_webhook(
                "page", PAGE_ID, [page_message("ps-1", "Again", PAGE_ID, mid="m2")]
            ),
        )
        assert stored(testbed, channel).status is ChannelStatus.CONNECTED

    def test_temporary_meta_failures_leave_the_channel_connected(self) -> None:
        testbed = ChannelsTestbed()
        owner = testbed.add_user("owner")
        business = testbed.add_business(owner)
        channel = testbed.add_channel(
            business.id, ChannelKind.MESSENGER, PAGE_ID, PAGE_ACCESS_TOKEN
        )
        testbed.meta_transport.respond(
            "POST",
            r"/me/messages$",
            {"error": {"message": "Please retry", "code": 2}},
            status_code=500,
        )

        post_meta(
            testbed,
            page_webhook("page", PAGE_ID, [page_message("ps-1", "Hi", PAGE_ID)]),
        )

        assert stored(testbed, channel).status is ChannelStatus.CONNECTED


def test_error_summaries_are_one_short_line() -> None:
    summary = summarize_channel_error("Line one\n  line two " + "x" * 400)

    assert "\n" not in str(summary)
    assert len(str(summary)) == 300
    assert str(summary).startswith("Line one line two x")
    assert str(summary).endswith("…")
    assert summarize_channel_error("   ") == (
        "The platform refused the channel's credential."
    )


class ReconnectedMidSendAdapter(TelegramChannelAdapter):
    """Telegram whose send races with the owner reconnecting a new bot token."""

    def __init__(
        self, testbed: ChannelsTestbed, channel: ChannelDocument, accepts: bool
    ) -> None:
        super().__init__(
            testbed.telegram_client, testbed.phone_number_parser, testbed.settings
        )
        self._testbed: ChannelsTestbed = testbed
        self._channel: ChannelDocument = channel
        self._accepts: bool = accepts

    def send(
        self, target: ChannelDeliveryTarget, text: MessageText
    ) -> DeliveredMessageCount:
        channel = stored(self._testbed, self._channel)
        channel.encrypted_secret = self._testbed.secret_cipher.encrypt(
            ChannelSecret(OTHER_TELEGRAM_BOT_TOKEN)
        )
        channel.status = ChannelStatus.CONNECTED
        channel.last_error = None
        channel.last_error_at = None
        self._testbed.channel_repo.save(channel)
        if not self._accepts:
            raise ChannelCredentialRejectedError("Telegram rejected the bot token.")

        return DeliveredMessageCount(1)


@pytest.mark.parametrize("accepts", [True, False])
def test_a_reconnect_during_a_send_is_not_undone_by_the_old_outcome(
    accepts: bool,
) -> None:
    testbed = ChannelsTestbed()
    business, channel = connect_bot(testbed)
    failing = stored(testbed, channel)
    failing.status = ChannelStatus.ERROR
    failing.last_error = summarize_channel_error("Telegram rejected the token.")
    testbed.channel_repo.save(failing)
    sender = ChannelMessageSenderFacilitator(
        testbed.channel_repo,
        testbed.secret_cipher,
        ReconnectedMidSendAdapter(testbed, channel, accepts),
        testbed.whatsapp_adapter,
        testbed.messenger_adapter,
        testbed.instagram_adapter,
        testbed.whatsapp_adapter,
        testbed.usage_event_repo,
        testbed.wall_clock,
    )

    def send() -> None:
        sender.send(
            business.id,
            ChannelKind.TELEGRAM,
            ChannelUserId("555000111"),
            MessageText("See you at 19:00."),
        )

    if accepts:
        send()
    else:
        with pytest.raises(ChannelCredentialRejectedError):
            send()

    reconnected = stored(testbed, channel)
    assert reconnected.status is ChannelStatus.CONNECTED
    assert reconnected.last_error is None
    assert reconnected.encrypted_secret is not None
    assert testbed.secret_cipher.decrypt(reconnected.encrypted_secret) == (
        OTHER_TELEGRAM_BOT_TOKEN
    )


class TestWhatsAppTemplateHealth:
    def test_revoked_token_on_a_template_marks_whatsapp_and_skips_english(
        self,
    ) -> None:
        testbed = ChannelsTestbed()
        owner = testbed.add_user("owner")
        business = testbed.add_business(owner)
        channel = testbed.add_channel(
            business.id, ChannelKind.WHATSAPP, "106540352242922"
        )
        testbed.meta_transport.respond(
            "POST",
            r"/messages$",
            {
                "error": {
                    "message": "Error validating access token: Session has expired.",
                    "type": "OAuthException",
                    "code": 190,
                }
            },
            status_code=401,
        )

        def send_reminder() -> None:
            testbed.channel_message_sender.send_whatsapp_template(
                business.id,
                ChannelUserId("995599123456"),
                WhatsAppTemplateName("booking_reminder"),
                LanguageTag("ka"),
                [MessageText("Salobie Bia")],
            )

        def template_usage() -> list[UsageKind]:
            return [
                event.kind
                for event in testbed.usage_event_repo.list_by_business_between(
                    business.id,
                    Microseconds(0),
                    Microseconds(int(testbed.clock.now_microseconds()) + 1),
                )
            ]

        with pytest.raises(ChannelCredentialRejectedError):
            send_reminder()

        [request] = testbed.meta_transport.requests  # no English retry
        assert json.loads(request.body)["template"]["language"]["code"] == "ka"
        broken = stored(testbed, channel)
        assert broken.status is ChannelStatus.ERROR
        assert "(190)" in str(broken.last_error)
        assert broken.last_error_at == testbed.clock.now_microseconds()
        assert template_usage() == []

        testbed.clock.advance(60)
        testbed.meta_transport.respond("POST", r"/messages$", {"messages": []})
        send_reminder()

        healed = stored(testbed, channel)
        assert healed.status is ChannelStatus.CONNECTED
        assert healed.last_error is None
        assert healed.last_error_at is None
        assert template_usage() == [UsageKind.WHATSAPP_TEMPLATE]
