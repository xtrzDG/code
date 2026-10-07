"""The Meta webhook route: verification handshake, signatures and routing."""

import pytest
from typed_time_provider import Microseconds

from app.schemas.constants.billing import UsageKind
from app.schemas.constants.channels import ChannelKind, ChannelStatus
from tests.channels.channels_settings import META_VERIFY_TOKEN, PAGE_ACCESS_TOKEN
from tests.channels.meta_payloads import (
    INSTAGRAM_ID,
    PAGE_ID,
    PHONE_NUMBER_ID,
    page_message,
    page_webhook,
    post_meta,
    whatsapp_message,
    whatsapp_webhook,
)
from tests.channels.testbed import ChannelsTestbed


class TestMetaWebhookVerification:
    def test_challenge_is_echoed_for_the_right_token(self) -> None:
        client = ChannelsTestbed().build_http_client()
        response = client.get(
            "/v1/channels/meta/webhook",
            params={
                "hub.mode": "subscribe",
                "hub.verify_token": META_VERIFY_TOKEN,
                "hub.challenge": "1158201444",
            },
        )

        assert response.status_code == 200
        assert response.text == "1158201444"

    @pytest.mark.parametrize(
        "params",
        [
            {"hub.mode": "subscribe", "hub.verify_token": "x", "hub.challenge": "1"},
            {
                "hub.mode": "other",
                "hub.verify_token": META_VERIFY_TOKEN,
                "hub.challenge": "1",
            },
            {"hub.mode": "subscribe", "hub.verify_token": META_VERIFY_TOKEN},
            {},
        ],
    )
    def test_wrong_verification_is_refused(self, params: dict[str, str]) -> None:
        client = ChannelsTestbed().build_http_client()
        assert client.get("/v1/channels/meta/webhook", params=params).status_code == 403


class TestMetaWebhook:
    def test_messages_are_routed_to_the_owning_business(self) -> None:
        testbed = ChannelsTestbed()
        owner_a, owner_b = testbed.add_user("a"), testbed.add_user("b")
        business_a = testbed.add_business(owner_a, name="Tbilisi Grill")
        business_b = testbed.add_business(owner_b, name="Warsaw Bistro")
        testbed.add_channel(business_a.id, ChannelKind.WHATSAPP, PHONE_NUMBER_ID)
        testbed.add_channel(business_b.id, ChannelKind.WHATSAPP, "200000000000002")
        testbed.meta_transport.respond("POST", r"/messages$", {"messages": []})

        response = post_meta(
            testbed,
            whatsapp_webhook([whatsapp_message("48512345678", "Dzień dobry")]),
        )
        testbed.run_worker()

        assert response.json()["queued"] == 1
        [inbound] = testbed.pipeline.messages
        assert inbound.business_id == business_a.id
        assert inbound.contact_phone_number == "+48512345678"
        [sent] = testbed.meta_transport.requests
        assert sent.path == f"/v23.0/{PHONE_NUMBER_ID}/messages"
        [usage] = testbed.usage_event_repo.list_by_business_between(
            business_a.id,
            testbed.clock.now_microseconds(),
            Microseconds(testbed.clock.now_microseconds() + 1),
        )
        assert usage.kind is UsageKind.WHATSAPP_REPLY
        assert usage.quantity == 1
        assert usage.conversation_id == testbed.pipeline.conversation_id

    def test_messages_for_unknown_or_disabled_accounts_are_dropped(self) -> None:
        testbed = ChannelsTestbed()
        owner = testbed.add_user("owner")
        business = testbed.add_business(owner)
        testbed.add_channel(
            business.id,
            ChannelKind.MESSENGER,
            PAGE_ID,
            PAGE_ACCESS_TOKEN,
            status=ChannelStatus.DISABLED,
        )

        unknown = post_meta(
            testbed,
            whatsapp_webhook([whatsapp_message("995599123456")], "999"),
        )
        disabled = post_meta(
            testbed,
            page_webhook("page", PAGE_ID, [page_message("psid", "Hi", PAGE_ID)]),
        )

        assert unknown.json()["received"] == 0
        assert disabled.json()["received"] == 0
        assert testbed.pipeline.messages == []

    def test_instagram_and_messenger_use_their_page_tokens(self) -> None:
        testbed = ChannelsTestbed()
        owner = testbed.add_user("owner")
        business = testbed.add_business(owner)
        testbed.add_channel(
            business.id, ChannelKind.MESSENGER, PAGE_ID, "messenger-token-0123456789"
        )
        testbed.add_channel(
            business.id, ChannelKind.INSTAGRAM, INSTAGRAM_ID, PAGE_ACCESS_TOKEN
        )
        testbed.meta_transport.respond("POST", r"/me/messages$", {"message_id": "m"})

        post_meta(
            testbed,
            page_webhook(
                "instagram", INSTAGRAM_ID, [page_message("ig-1", "Hi", INSTAGRAM_ID)]
            ),
        )
        post_meta(
            testbed,
            page_webhook(
                "page", PAGE_ID, [page_message("ps-1", "Hi", PAGE_ID, mid="m2")]
            ),
        )
        testbed.run_worker()

        tokens = [r.headers["Authorization"] for r in testbed.meta_transport.requests]
        assert tokens == [
            f"Bearer {PAGE_ACCESS_TOKEN}",
            "Bearer messenger-token-0123456789",
        ]
        assert [m.channel for m in testbed.pipeline.messages] == [
            ChannelKind.INSTAGRAM,
            ChannelKind.MESSENGER,
        ]
        assert (
            testbed.usage_event_repo.list_by_business_between(
                business.id,
                testbed.clock.now_microseconds(),
                Microseconds(testbed.clock.now_microseconds() + 1),
            )
            == []
        )

    @pytest.mark.parametrize("signature", [None, "sha256=00", "garbage"])
    def test_unsigned_or_wrongly_signed_deliveries_are_refused(
        self, signature: str | None
    ) -> None:
        testbed = ChannelsTestbed()
        response = post_meta(
            testbed, whatsapp_webhook([whatsapp_message("1")]), signature=signature
        )
        assert response.status_code == 401

    def test_signed_unknown_objects_are_acknowledged_and_ignored(self) -> None:
        testbed = ChannelsTestbed()
        response = post_meta(testbed, {"object": "user", "entry": []})
        assert response.status_code == 200
        assert response.json()["received"] == 0
        assert post_meta(testbed, {"object": "user"}, signature=None).status_code == 401

    def test_repeated_delivery_and_staff_silence(self) -> None:
        testbed = ChannelsTestbed()
        owner = testbed.add_user("owner")
        business = testbed.add_business(owner)
        testbed.add_channel(business.id, ChannelKind.WHATSAPP, PHONE_NUMBER_ID)
        testbed.pipeline.is_silent = True
        payload = whatsapp_webhook([whatsapp_message("995599123456")])

        first = post_meta(testbed, payload)
        second = post_meta(testbed, payload)
        testbed.run_worker()

        assert first.json()["queued"] == 1
        assert second.json()["duplicates"] == 1
        assert len(testbed.pipeline.messages) == 1
        assert testbed.meta_transport.requests == []
