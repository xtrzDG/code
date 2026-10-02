"""What the inbox records for each message: answered, silent, refused, recovered."""

import pytest

from app.schemas.constants.channels import ChannelKind
from app.schemas.constants.deliveries import InboundEventKind, InboundEventStatus
from app.schemas.exceptions.application_errors import ConflictError
from tests.channels.outbox_reads import inbox
from tests.channels.platform_bot_setup import PlatformBotSetup
from tests.channels.telegram_updates import build_update, connect_bot, post_update
from tests.channels.test_widget import SESSION_KEY, enable_widget
from tests.channels.testbed import ChannelsTestbed
from tests.channels.widget_polling_steps import poll, send

PAST_THE_LEASE_SECONDS: int = 180


def test_answered_and_silent_messages_are_closed() -> None:
    testbed = ChannelsTestbed()
    business, channel = connect_bot(testbed)

    post_update(testbed, channel, build_update(message_id=1))
    testbed.run_worker()
    testbed.pipeline.is_silent = True
    post_update(testbed, channel, build_update(message_id=2))
    testbed.run_worker()

    answered, silent = inbox(testbed)
    assert answered.status is InboundEventStatus.ANSWERED
    assert answered.business_id == business.id
    assert answered.channel_id == channel.id
    assert answered.provider_message_id == "555000111:1"
    assert answered.conversation_id == testbed.pipeline.conversation_id
    assert answered.outbound_message_id is not None
    assert answered.processed_at is not None
    assert answered.lease_until is None
    assert silent.status is InboundEventStatus.HANDED_OFF
    assert silent.outbound_message_id is None


def test_a_refusal_fails_the_message_without_retries() -> None:
    testbed = ChannelsTestbed()
    _, channel = connect_bot(testbed)
    testbed.pipeline.failure = ConflictError(
        "The assistant of Funicular VR is not live."
    )

    post_update(testbed, channel, build_update())
    testbed.run_worker()
    testbed.clock.advance(3600)
    testbed.run_worker()

    [failed] = inbox(testbed)
    assert failed.status is InboundEventStatus.FAILED
    assert str(failed.last_error) == "The assistant of Funicular VR is not live."
    assert failed.attempts == 1
    assert len(testbed.pipeline.messages) == 1


def test_platform_events_are_kept_until_the_worker_handles_them() -> None:
    setup = PlatformBotSetup()

    setup.send_to_bot("hello")

    [event] = inbox(setup.testbed)
    assert event.kind is InboundEventKind.PLATFORM_BOT_UPDATE
    assert event.business_id is None
    assert event.channel is ChannelKind.TELEGRAM
    assert event.status is InboundEventStatus.ANSWERED
    assert setup.replies()[0].startswith("Hello!")


class TestWidgetInbox:
    def test_the_widget_answers_at_once_and_records_the_message(self) -> None:
        testbed = ChannelsTestbed()
        business = enable_widget(testbed)

        reply = send(testbed.build_http_client(), business.id, "Shalom")

        assert reply["text"] == "Reply: Shalom"
        [event] = inbox(testbed)
        assert event.channel is ChannelKind.WEB_CHAT
        assert event.status is InboundEventStatus.ANSWERED
        assert event.outbound_message_id is None  # the widget polls, no push
        assert reply["message_id"] == str(event.reply_message_id)

        # The safety job finds the message answered and does nothing.
        testbed.clock.advance(PAST_THE_LEASE_SECONDS)
        testbed.run_worker()
        assert len(testbed.pipeline.messages) == 1

    def test_a_crash_during_the_turn_is_answered_by_the_worker(self) -> None:
        testbed = ChannelsTestbed()
        business = enable_widget(testbed)
        client = testbed.build_http_client()
        testbed.pipeline.crashing_texts = {"Shalom"}

        with pytest.raises(RuntimeError):
            client.post(
                f"/v1/widget/{business.id}/messages",
                json={"session_key": SESSION_KEY, "text": "Shalom"},
            )

        [held] = inbox(testbed)
        assert held.status is InboundEventStatus.PROCESSING
        testbed.pipeline.crashing_texts = set()
        testbed.run_worker()
        assert len(testbed.pipeline.messages) == 1  # held until the lease ends

        testbed.clock.advance(PAST_THE_LEASE_SECONDS)
        testbed.run_worker()

        [recovered] = inbox(testbed)
        assert recovered.status is InboundEventStatus.ANSWERED
        # The visitor's widget keeps polling and shows the late answer.
        polled = poll(client, business.id, after=str(recovered.customer_message_id))
        assert [item["text"] for item in polled.json()["items"]] == ["Reply: Shalom"]

    def test_a_refused_widget_message_is_closed_as_failed(self) -> None:
        testbed = ChannelsTestbed()
        business = enable_widget(testbed)
        testbed.pipeline.failure = ConflictError("not live")

        response = testbed.build_http_client().post(
            f"/v1/widget/{business.id}/messages",
            json={"session_key": SESSION_KEY, "text": "Shalom"},
        )
        testbed.clock.advance(PAST_THE_LEASE_SECONDS)
        testbed.run_worker()

        assert response.status_code == 409
        [failed] = inbox(testbed)
        assert failed.status is InboundEventStatus.FAILED
        assert len(testbed.pipeline.messages) == 1
