from typing import Any

import pytest

from app.schemas.constants.businesses import BusinessStatus
from app.schemas.constants.channels import ChannelKind, ChannelStatus
from app.schemas.constants.deliveries import InboundEventStatus
from app.schemas.typings.localization.constrained_strings import LanguageTag
from tests.channels.channels_payloads import bearer
from tests.channels.channels_settings import ISRAEL, POLAND, build_settings
from tests.channels.outbox_reads import inbox
from tests.channels.testbed import ChannelsTestbed

SESSION_KEY: str = "v1_9f2c4e1b7a3d48c6"


def enable_widget(testbed: ChannelsTestbed, country: Any = ISRAEL) -> Any:
    owner_id = testbed.add_user("owner")
    business = testbed.add_business(owner_id, country=country, name="Jaffa Port Café")
    business.status = BusinessStatus.LIVE
    testbed.business_repo.save(business)
    testbed.add_channel(business.id, ChannelKind.WEB_CHAT)
    return business


def poll_answers(client: Any, business_id: object) -> list[dict[str, Any]]:
    """What the widget's polling shows after the visitor's own message."""

    headers = {"X-Widget-Session-Key": SESSION_KEY}
    path = f"/v1/widget/{business_id}/messages"
    position = client.get(path, headers=headers).json()["cursor"]
    page = client.get(path, headers=headers, params={"after": position}).json()
    return [page]


class TestWidgetConfig:
    def test_right_to_left_languages_are_marked(self) -> None:
        testbed = ChannelsTestbed()
        business = enable_widget(testbed)

        response = testbed.build_http_client().get(f"/v1/widget/{business.id}/config")

        assert response.status_code == 200
        assert response.headers["Access-Control-Allow-Origin"] == "*"
        body = response.json()
        assert body["business_name"] == "Jaffa Port Café"
        assert body["is_enabled"] is True
        assert body["accent_color"] is None
        assert body["position"] is None
        assert body["default_language"] == "he"
        assert [(item["tag"], item["direction"]) for item in body["languages"]] == [
            ("he", "rtl"),
            ("ar", "rtl"),
            ("en", "ltr"),
        ]
        assert body["languages"][0]["native_name"] == "עברית"

    def test_disabled_widget_reports_itself_off(self) -> None:
        testbed = ChannelsTestbed()
        owner_id = testbed.add_user("owner")
        business = testbed.add_business(owner_id, country=POLAND)
        testbed.add_channel(
            business.id, ChannelKind.WEB_CHAT, status=ChannelStatus.DISABLED
        )

        body = (
            testbed.build_http_client().get(f"/v1/widget/{business.id}/config").json()
        )

        assert body["is_enabled"] is False
        assert [item["direction"] for item in body["languages"]] == ["ltr", "ltr"]

    def test_unknown_business_is_not_found(self) -> None:
        client = ChannelsTestbed().build_http_client()
        assert client.get("/v1/widget/business_nope/config").status_code == 404
        assert (
            client.get(
                "/v1/widget/business_00000000-0000-4000-8000-000000000000/config"
            ).status_code
            == 404
        )

    def test_preflight_allows_any_site(self) -> None:
        testbed = ChannelsTestbed()
        business = enable_widget(testbed)

        response = testbed.build_http_client().options(
            f"/v1/widget/{business.id}/messages"
        )

        assert response.status_code == 204
        assert response.headers["Access-Control-Allow-Origin"] == "*"
        assert "POST" in response.headers["Access-Control-Allow-Methods"]


class TestWidgetMessages:
    def test_a_message_is_queued_for_the_worker_and_accepted_at_once(self) -> None:
        testbed = ChannelsTestbed()
        business = enable_widget(testbed)
        testbed.pipeline.language = LanguageTag("he")
        client = testbed.build_http_client()

        response = client.post(
            f"/v1/widget/{business.id}/messages",
            json={
                "session_key": SESSION_KEY,
                "text": "יש מקום לשניים?",
                "contact_name": "  Dana ",
            },
        )

        assert response.status_code == 202
        assert response.headers["Access-Control-Allow-Origin"] == "*"
        [event] = inbox(testbed)
        assert response.json() == {"event_id": str(event.id)}
        # Nothing was answered in the request: the inbox holds it for a worker.
        assert event.status is InboundEventStatus.RECEIVED
        assert testbed.pipeline.messages == []

        testbed.run_worker()

        [inbound] = testbed.pipeline.messages
        assert inbound.business_id == business.id
        assert inbound.channel is ChannelKind.WEB_CHAT
        assert inbound.channel_user_id == SESSION_KEY
        assert inbound.contact_name == "Dana"
        [page] = poll_answers(client, business.id)
        [answer] = page["items"]
        assert (answer["text"], answer["direction"], answer["author"]) == (
            "Reply: יש מקום לשניים?",
            "rtl",
            "assistant",
        )

    def test_plain_text_content_type_avoids_the_preflight(self) -> None:
        testbed = ChannelsTestbed()
        business = enable_widget(testbed)

        response = testbed.build_http_client().post(
            f"/v1/widget/{business.id}/messages",
            content=f'{{"session_key": "{SESSION_KEY}", "text": "Hi"}}',
            headers={"Content-Type": "text/plain"},
        )

        assert response.status_code == 202

    def test_while_staff_handle_the_chat_the_widget_hears_no_answer(self) -> None:
        testbed = ChannelsTestbed()
        business = enable_widget(testbed)
        testbed.pipeline.is_silent = True
        client = testbed.build_http_client()

        accepted = client.post(
            f"/v1/widget/{business.id}/messages",
            json={"session_key": SESSION_KEY, "text": "Hello?"},
        )
        testbed.run_worker()

        assert accepted.status_code == 202
        [page] = poll_answers(client, business.id)
        assert page["items"] == []
        assert page["is_handed_off"] is True
        [event] = inbox(testbed)
        assert event.status is InboundEventStatus.HANDED_OFF

    def test_an_assistant_that_is_not_live_refuses_at_once(self) -> None:
        testbed = ChannelsTestbed()
        business = enable_widget(testbed)
        business.status = BusinessStatus.TESTING
        testbed.business_repo.save(business)

        response = testbed.build_http_client().post(
            f"/v1/widget/{business.id}/messages",
            json={"session_key": SESSION_KEY, "text": "Hi"},
        )

        # The widget says the chat is unavailable instead of typing forever.
        assert response.status_code == 409
        assert inbox(testbed) == []

    def test_disabled_widget_and_unknown_business_are_unavailable(self) -> None:
        testbed = ChannelsTestbed()
        owner_id = testbed.add_user("owner")
        without_widget = testbed.add_business(owner_id)
        client = testbed.build_http_client()

        for business_id in (str(without_widget.id), "business_unknown"):
            response = client.post(
                f"/v1/widget/{business_id}/messages",
                json={"session_key": SESSION_KEY, "text": "Hi"},
            )
            assert response.status_code == 404

        assert testbed.pipeline.messages == []

    @pytest.mark.parametrize(
        "body",
        [
            {"session_key": SESSION_KEY, "text": ""},
            {"session_key": SESSION_KEY, "text": "   "},
            {"session_key": SESSION_KEY, "text": "x" * 4001},
            {"session_key": "short", "text": "Hi"},
            {"session_key": "has spaces in the key!", "text": "Hi"},
            {"session_key": SESSION_KEY, "text": "Hi", "contact_name": "n" * 101},
            {"session_key": SESSION_KEY},
            {"session_key": SESSION_KEY, "text": "Hi", "extra": True},
        ],
    )
    def test_invalid_messages_are_rejected(self, body: dict[str, Any]) -> None:
        testbed = ChannelsTestbed()
        business = enable_widget(testbed)

        response = testbed.build_http_client().post(
            f"/v1/widget/{business.id}/messages", json=body
        )

        assert response.status_code == 422
        assert testbed.pipeline.messages == []


class TestWidgetSnippet:
    def test_owner_and_staff_get_the_embed_code(self) -> None:
        testbed = ChannelsTestbed()
        owner_id = testbed.add_user("owner")
        staff_id = testbed.add_user("staff")
        business = testbed.add_business(owner_id, staff_ids=[staff_id])
        client = testbed.build_http_client()

        for token in ("owner", "staff"):
            response = client.get(
                f"/v1/businesses/{business.id}/channels/web/snippet",
                headers=bearer(token),
            )
            assert response.status_code == 200
            body = response.json()
            assert body["script_url"] == "https://api.workshop.test/widget.js"
            assert body["snippet"] == (
                '<script src="https://api.workshop.test/widget.js" '
                f'data-tenant="{business.id}" async></script>'
            )
            assert body["demo_url"] == (
                f"https://api.workshop.test/widget/demo?business_id={business.id}"
            )

    def test_strangers_and_anonymous_users_get_nothing(self) -> None:
        testbed = ChannelsTestbed()
        owner_id = testbed.add_user("owner")
        testbed.add_user("stranger")
        business = testbed.add_business(owner_id)
        client = testbed.build_http_client()
        path = f"/v1/businesses/{business.id}/channels/web/snippet"

        assert client.get(path, headers=bearer("stranger")).status_code == 404
        assert client.get(path).status_code == 401

    def test_missing_base_url_is_reported(self) -> None:
        testbed = ChannelsTestbed(build_settings(APP_BASE_URL=""))
        owner_id = testbed.add_user("owner")
        business = testbed.add_business(owner_id)

        response = testbed.build_http_client().get(
            f"/v1/businesses/{business.id}/channels/web/snippet",
            headers=bearer("owner"),
        )

        assert response.status_code == 502
        assert "APP_BASE_URL" in response.json()["message"]
