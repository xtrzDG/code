"""
The health line of a channel: when it last brought a customer message and
carried one of ours (to the minute), and what its last error means.
"""

from app.schemas.constants.channels import ChannelKind, ChannelStatus
from app.schemas.constants.deliveries import DeliveryFailureReason
from app.schemas.typings.channels.constrained_strings import ChannelErrorSummary
from app.use_cases.channels.channel_views import build_channel_view
from app.utilities.channels.channel_activity import (
    ACTIVITY_STAMP_RESOLUTION_MICROSECONDS,
    is_stamp_due,
)
from app.utilities.channels.delivery_targets import find_business_channel
from tests.channels.channels_payloads import bearer, telegram_ok
from tests.channels.stored_channels import stored
from tests.channels.telegram_updates import build_update, connect_bot, post_update
from tests.channels.test_widget import SESSION_KEY, enable_widget
from tests.channels.testbed import ChannelsTestbed

REVOKED: dict[str, object] = {"ok": False, "error_code": 401, "description": "No"}


def test_a_stamp_is_due_without_one_and_after_a_minute() -> None:
    minute = ACTIVITY_STAMP_RESOLUTION_MICROSECONDS
    now = 10 * minute

    assert is_stamp_due(None, now) is True  # type: ignore[arg-type]
    assert is_stamp_due(now - minute + 1, now) is False  # type: ignore[arg-type]
    assert is_stamp_due(now - minute, now) is True  # type: ignore[arg-type]
    # A clock that moved back (another instance) does not freeze the stamp.
    assert is_stamp_due(now + 5, now) is True  # type: ignore[arg-type]


def test_a_telegram_channel_notes_customer_messages_and_delivered_replies() -> None:
    testbed = ChannelsTestbed()
    business, channel = connect_bot(testbed)
    testbed.telegram_transport.respond("POST", r"/sendMessage$", telegram_ok({}))
    first_at = testbed.clock.now_microseconds()

    post_update(testbed, channel, build_update(message_id=1))
    testbed.run_worker()
    testbed.clock.advance(20)
    post_update(testbed, channel, build_update(message_id=2))
    testbed.run_worker()

    within_a_minute = stored(testbed, channel)
    first_reply_at = within_a_minute.last_outbound_at
    assert within_a_minute.last_inbound_at == first_at
    # The worker's steps take a few clock ticks; the reply stays in the
    # minute of the first one.
    assert first_reply_at is not None
    assert 0 <= int(first_reply_at) - int(first_at) < 1_000_000

    testbed.clock.advance(61)
    second_at = testbed.clock.now_microseconds()
    post_update(testbed, channel, build_update(message_id=3))
    testbed.run_worker()

    later = stored(testbed, channel)
    assert later.last_inbound_at == second_at
    assert later.last_outbound_at is not None
    assert int(later.last_outbound_at) >= int(second_at)
    [view] = (
        testbed.build_http_client()
        .get(f"/v1/businesses/{business.id}/channels", headers=bearer("owner"))
        .json()
    )
    assert view["last_inbound_at"] == int(second_at)
    assert view["last_outbound_at"] == int(later.last_outbound_at)
    assert view["last_error_reason"] is None


def test_a_refused_reply_is_inbound_activity_only_and_says_why() -> None:
    testbed = ChannelsTestbed()
    _, channel = connect_bot(testbed)
    testbed.telegram_transport.respond(
        "POST", r"/sendMessage$", REVOKED, status_code=401
    )

    received_at = testbed.clock.now_microseconds()
    post_update(testbed, channel, build_update())
    testbed.run_worker()

    broken = stored(testbed, channel)
    assert broken.status is ChannelStatus.ERROR
    assert broken.last_error_reason is DeliveryFailureReason.CREDENTIAL_REJECTED
    assert broken.last_inbound_at == received_at
    assert broken.last_outbound_at is None

    testbed.clock.advance(90)
    healed_from = testbed.clock.now_microseconds()
    testbed.telegram_transport.respond("POST", r"/sendMessage$", telegram_ok({}))
    post_update(testbed, channel, build_update(message_id=9))
    testbed.run_worker()

    healed = stored(testbed, channel)
    assert healed.status is ChannelStatus.CONNECTED
    assert (healed.last_error, healed.last_error_reason) == (None, None)
    assert healed.last_outbound_at is not None
    assert int(healed.last_outbound_at) >= int(healed_from)


def test_a_customer_who_blocked_the_bot_is_a_refusal_not_a_broken_channel() -> None:
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
    assert refused.last_error_reason is DeliveryFailureReason.RECIPIENT_REFUSED
    assert build_channel_view(refused).last_error_reason is (
        DeliveryFailureReason.RECIPIENT_REFUSED
    )


def test_the_website_chat_notes_visitor_messages_and_answers() -> None:
    testbed = ChannelsTestbed()
    business = enable_widget(testbed)
    client = testbed.build_http_client()

    accepted = client.post(
        f"/v1/widget/{business.id}/messages",
        json={"session_key": SESSION_KEY, "text": "Hello"},
    )
    web_chat = find_business_channel(
        testbed.channel_repo, business.id, ChannelKind.WEB_CHAT
    )
    assert web_chat is not None
    assert web_chat.last_inbound_at == testbed.clock.now_microseconds()
    assert web_chat.last_outbound_at is None

    testbed.clock.advance(5)
    answering_from = testbed.clock.now_microseconds()
    testbed.run_worker()

    answered = find_business_channel(
        testbed.channel_repo, business.id, ChannelKind.WEB_CHAT
    )
    assert accepted.status_code == 202
    assert answered is not None
    assert answered.last_outbound_at is not None
    assert int(answered.last_outbound_at) >= int(answering_from)


def test_an_error_kept_before_reasons_were_stored_is_read_as_a_refused_key() -> None:
    testbed = ChannelsTestbed()
    _, channel = connect_bot(testbed)
    old = stored(testbed, channel)
    old.status = ChannelStatus.ERROR
    old.last_error = ChannelErrorSummary("Telegram rejected the bot token (401).")
    refusal = old.model_copy(
        update={
            "status": ChannelStatus.CONNECTED,
            "last_error": ChannelErrorSummary("Forbidden: blocked"),
        }
    )
    clean = old.model_copy(
        update={"status": ChannelStatus.CONNECTED, "last_error": None}
    )

    assert build_channel_view(old).last_error_reason is (
        DeliveryFailureReason.CREDENTIAL_REJECTED
    )
    assert build_channel_view(refusal).last_error_reason is None
    assert build_channel_view(clean).last_error_reason is None
