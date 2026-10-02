"""Meta channels and WhatsApp templates refused by the platform turn ERROR and heal."""

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
from app.schemas.dto.channels.channel_webhooks import (
    ChannelDeliveryTarget,
    ChannelSendReceipt,
)
from app.schemas.exceptions.application_errors import ChannelCredentialRejectedError
from app.schemas.typings.channels.constrained_integers import DeliveredMessageCount
from app.schemas.typings.channels.constrained_strings import WhatsAppTemplateName
from app.schemas.typings.channels.strings import ChannelSecret
from app.schemas.typings.conversations.strings import ChannelUserId, MessageText
from app.schemas.typings.localization.constrained_strings import LanguageTag
from app.utilities.channels.channel_health import summarize_channel_error
from tests.channels.channels_settings import OTHER_TELEGRAM_BOT_TOKEN, PAGE_ACCESS_TOKEN
from tests.channels.meta_payloads import PAGE_ID, page_message, page_webhook, post_meta
from tests.channels.stored_channels import stored
from tests.channels.telegram_updates import connect_bot
from tests.channels.testbed import ChannelsTestbed


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
        testbed.run_worker()

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
        testbed.run_worker()
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
        testbed.run_worker()

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
    ) -> ChannelSendReceipt:
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

        return ChannelSendReceipt(delivered=DeliveredMessageCount(1))


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
