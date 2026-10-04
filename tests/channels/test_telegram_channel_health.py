"""A Telegram channel whose bot token is refused turns ERROR and heals itself."""

from app.schemas.constants.channels import ChannelStatus
from app.schemas.constants.deliveries import (
    DeliveryFailureReason,
    OutboundMessageKind,
    OutboundMessageStatus,
)
from app.schemas.constants.handoffs import HandoffSummaryCode
from app.schemas.dto.handoffs import CodedHandoffSummary
from app.utilities.channels.channel_health import summarize_channel_error
from tests.channels.channels_payloads import bearer, telegram_ok
from tests.channels.channels_settings import TELEGRAM_BOT_TOKEN
from tests.channels.customer_outbox import queue_customer_message
from tests.channels.outbox_reads import outbox_of
from tests.channels.stored_channels import stored
from tests.channels.telegram_updates import build_update, connect_bot, post_update
from tests.channels.testbed import ChannelsTestbed

REVOKED: dict[str, object] = {
    "ok": False,
    "error_code": 401,
    "description": "Unauthorized",
}


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
        testbed.run_worker()

        assert failed.status_code == 200
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
        testbed.run_worker()

        assert answered.json()["queued"] == 1
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
        testbed.run_worker()

        refused = stored(testbed, channel)
        assert refused.status is ChannelStatus.CONNECTED
        # The owner sees why; staff are asked to reach the customer.
        assert refused.last_error == (
            "Telegram sendMessage refused the request (403): Forbidden: blocked"
        )
        [handoff] = testbed.handoffs_to_human.commands
        assert isinstance(handoff.summary, CodedHandoffSummary)
        assert handoff.summary.code is HandoffSummaryCode.REPLY_UNDELIVERED

    def test_messages_the_business_starts_also_track_the_channel(self) -> None:
        testbed = ChannelsTestbed()
        business, channel = connect_bot(testbed)
        testbed.telegram_transport.respond(
            "POST", r"/sendMessage$", REVOKED, status_code=401
        )

        queue_customer_message(
            testbed, channel, "555000111", OutboundMessageKind.CALL_CONFIRMATION
        )
        testbed.run_worker()

        assert stored(testbed, channel).status is ChannelStatus.ERROR
        testbed.telegram_transport.respond("POST", r"/sendMessage$", telegram_ok({}))
        queue_customer_message(
            testbed, channel, "555000111", OutboundMessageKind.BOOKING_REMINDER
        )
        testbed.run_worker()
        assert stored(testbed, channel).status is ChannelStatus.CONNECTED
        by_kind = {message.kind: message for message in outbox_of(testbed, business.id)}
        refused = by_kind[OutboundMessageKind.CALL_CONFIRMATION]
        assert refused.last_failure_reason is DeliveryFailureReason.CREDENTIAL_REJECTED
        delivered = by_kind[OutboundMessageKind.BOOKING_REMINDER]
        assert delivered.status is OutboundMessageStatus.DELIVERED

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

        queue_customer_message(
            testbed, channel, "555000111", OutboundMessageKind.CALL_LINKS
        )
        testbed.run_worker()

        [message] = outbox_of(testbed, business.id)
        assert message.status is OutboundMessageStatus.DEAD
        assert message.last_failure_reason is (
            DeliveryFailureReason.CHANNEL_DISCONNECTED
        )
        assert "no longer connected" in str(message.last_error)
        assert stored(testbed, channel).status is ChannelStatus.DISABLED
        assert testbed.telegram_transport.requests_to("/sendMessage") == []
