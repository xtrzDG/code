"""Where a customer came from, captured per channel and carried to the engine."""

from typing import Any

from app.schemas.constants.channels import ChannelKind
from app.schemas.dto.channels.channel_webhooks import (
    ChannelInboundMessage,
    ChannelWebhookPayload,
)
from tests.channels.channels_payloads import to_json_bytes
from tests.channels.meta_payloads import (
    INSTAGRAM_ID,
    PAGE_ID,
    page_message,
    page_webhook,
    whatsapp_message,
    whatsapp_webhook,
)
from tests.channels.post_call_steps import (
    add_booking,
    post_call_payload,
    process_call,
    stored_calls,
)
from tests.channels.telegram_updates import build_update, connect_bot, post_update
from tests.channels.test_widget import SESSION_KEY, enable_widget
from tests.channels.testbed import ChannelsTestbed
from tests.channels.voice_setup import build_voice_setup


def parse(adapter: Any, payload: dict[str, Any]) -> list[ChannelInboundMessage]:
    messages: list[ChannelInboundMessage] = adapter.parse_webhook(
        ChannelWebhookPayload(body=to_json_bytes(payload))
    )
    return messages


class TestTelegram:
    def test_a_tagged_start_link_reaches_the_engine_with_its_source(self) -> None:
        testbed = ChannelsTestbed()
        _, channel = connect_bot(testbed)

        post_update(testbed, channel, build_update(text="/start src_qr-tables"))
        testbed.run_worker()

        [inbound] = testbed.pipeline.messages
        assert inbound.acquisition_source == "qr-tables"
        # The assistant reads what the customer saw: "/start".
        assert inbound.text == "/start"

    def test_other_messages_carry_no_source(self) -> None:
        testbed = ChannelsTestbed()
        _, channel = connect_bot(testbed)

        post_update(testbed, channel, build_update(text="/start promo"))
        testbed.run_worker()

        [inbound] = testbed.pipeline.messages
        assert inbound.acquisition_source is None
        assert inbound.text == "/start promo"


class TestWhatsApp:
    def test_the_code_of_a_tagged_link_is_read_from_the_greeting(self) -> None:
        adapter = ChannelsTestbed().whatsapp_adapter
        payload = whatsapp_webhook(
            [whatsapp_message("995599123456", text="Здравствуйте! (#qr-tables)")]
        )

        [message] = parse(adapter, payload)

        assert message.acquisition_source == "qr-tables"
        assert message.text == "Здравствуйте!"

    def test_a_click_to_whatsapp_ad_wins_over_the_code(self) -> None:
        adapter = ChannelsTestbed().whatsapp_adapter
        referral = {
            "source_url": "https://fb.me/abc",
            "source_id": "120208",
            "source_type": "ad",
            "headline": "Dinner for two",
        }
        payload = whatsapp_webhook(
            [
                whatsapp_message(
                    "995599123456",
                    text="Hi! (#qr)",
                    extra={"referral": referral},
                ),
                whatsapp_message("995599123457", text="Plain hello", message_id="w2"),
            ]
        )

        first, second = parse(adapter, payload)

        assert first.acquisition_source == "ad-120208"
        assert second.acquisition_source is None


class TestMetaPages:
    def test_a_get_started_postback_of_a_tagged_link(self) -> None:
        adapter = ChannelsTestbed().messenger_adapter
        event = {
            "sender": {"id": "psid-1"},
            "recipient": {"id": PAGE_ID},
            "postback": {
                "title": "Get Started",
                "payload": "GET_STARTED",
                "mid": "m1",
                "referral": {"ref": "flyer", "source": "SHORTLINK"},
            },
        }

        [message] = parse(adapter, page_webhook("page", PAGE_ID, [event]))

        assert message.channel is ChannelKind.MESSENGER
        assert message.acquisition_source == "flyer"

    def test_an_ad_click_on_the_event_or_the_message(self) -> None:
        adapter = ChannelsTestbed().instagram_adapter
        on_event = page_message("igsid-1", "Hello", INSTAGRAM_ID, mid="m1")
        on_event["referral"] = {"source": "ADS", "ad_id": "6045246247433"}
        on_message = page_message("igsid-2", "Price?", INSTAGRAM_ID, mid="m2")
        on_message["message"]["referral"] = {"ref": "bio", "source": "IGME"}
        plain = page_message("igsid-3", "Hi", INSTAGRAM_ID, mid="m3")

        messages = parse(
            adapter,
            page_webhook("instagram", INSTAGRAM_ID, [on_event, on_message, plain]),
        )

        assert [message.acquisition_source for message in messages] == [
            "ad-6045246247433",
            "bio",
            None,
        ]

    def test_a_referral_without_a_message_has_nothing_to_answer(self) -> None:
        adapter = ChannelsTestbed().messenger_adapter
        event = {
            "sender": {"id": "psid-1"},
            "recipient": {"id": PAGE_ID},
            "referral": {"ref": "qr", "source": "SHORTLINK", "type": "OPEN_THREAD"},
        }

        assert parse(adapter, page_webhook("page", PAGE_ID, [event])) == []


class TestWidget:
    def send(self, testbed: ChannelsTestbed, business: Any, **extra: Any) -> Any:
        return testbed.build_http_client().post(
            f"/v1/widget/{business.id}/messages",
            json={"session_key": SESSION_KEY, "text": "Hello", **extra},
        )

    def test_the_page_source_goes_with_the_message(self) -> None:
        testbed = ChannelsTestbed()
        business = enable_widget(testbed)

        response = self.send(testbed, business, source="  QR Tables ")
        testbed.run_worker()

        assert response.status_code == 202
        [inbound] = testbed.pipeline.messages
        assert inbound.acquisition_source == "qr-tables"

    def test_an_unreadable_source_never_refuses_the_message(self) -> None:
        testbed = ChannelsTestbed()
        business = enable_widget(testbed)

        accepted = self.send(testbed, business, source="!!!")
        too_long = self.send(testbed, business, source="x" * 201)
        testbed.run_worker()

        assert accepted.status_code == 202
        assert too_long.status_code == 422
        [inbound] = testbed.pipeline.messages
        assert inbound.acquisition_source is None


class TestPhone:
    def test_a_tool_calls_conversation_comes_from_the_line_dialled(self) -> None:
        setup = build_voice_setup()
        add_booking(setup)

        process_call(setup, post_call_payload(tool_names=("create_booking",)))

        stored = setup.testbed.conversation_repo.get(
            setup.business.id, setup.conversation.id
        )
        assert stored is not None
        assert stored.acquisition_source == "tel-995322000000"

    def test_a_call_without_tools_opens_its_conversation_with_the_line(self) -> None:
        setup = build_voice_setup()

        body = process_call(setup, post_call_payload("conv_info"))

        [call] = [
            call
            for call in stored_calls(setup)
            if str(call.provider_call_id) == "conv_info"
        ]
        assert body["outcome"] == "information"
        assert call.conversation_id is not None
        opened = setup.testbed.conversation_repo.get(
            setup.business.id, call.conversation_id
        )
        assert opened is not None
        assert opened.acquisition_source == "tel-995322000000"
