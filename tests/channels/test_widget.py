from typing import Any

import pytest

from app.schemas.constants.channels import ChannelKind, ChannelStatus
from app.schemas.typings.localization.constrained_strings import LanguageTag
from tests.channels.testbed import (
    ISRAEL,
    POLAND,
    ChannelsTestbed,
    bearer,
    build_settings,
)

SESSION_KEY: str = "v1_9f2c4e1b7a3d48c6"


def enable_widget(testbed: ChannelsTestbed, country: Any = ISRAEL) -> Any:
    owner_id = testbed.add_user("owner")
    business = testbed.add_business(owner_id, country=country, name="Jaffa Port Café")
    testbed.add_channel(business.id, ChannelKind.WEB_CHAT)
    return business


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
    def test_visitor_message_is_answered_with_the_text_direction(self) -> None:
        testbed = ChannelsTestbed()
        business = enable_widget(testbed)
        testbed.pipeline.language = LanguageTag("he")

        response = testbed.build_http_client().post(
            f"/v1/widget/{business.id}/messages",
            json={
                "session_key": SESSION_KEY,
                "text": "יש מקום לשניים?",
                "contact_name": "  Dana ",
            },
        )

        assert response.status_code == 200
        assert response.headers["Access-Control-Allow-Origin"] == "*"
        visitor_message, answer = testbed.message_repo.list_by_conversation(
            business.id, testbed.pipeline.conversation_id
        )
        assert response.json() == {
            "conversation_id": str(testbed.pipeline.conversation_id),
            "text": "Reply: יש מקום לשניים?",
            "language": "he",
            "direction": "rtl",
            "is_handed_off": False,
            "message_id": str(answer.id),
            "cursor": str(visitor_message.id),
        }
        [inbound] = testbed.pipeline.messages
        assert inbound.business_id == business.id
        assert inbound.channel is ChannelKind.WEB_CHAT
        assert inbound.channel_user_id == SESSION_KEY
        assert inbound.contact_name == "Dana"

    def test_plain_text_content_type_avoids_the_preflight(self) -> None:
        testbed = ChannelsTestbed()
        business = enable_widget(testbed)

        response = testbed.build_http_client().post(
            f"/v1/widget/{business.id}/messages",
            content=f'{{"session_key": "{SESSION_KEY}", "text": "Hi"}}',
            headers={"Content-Type": "text/plain"},
        )

        assert response.status_code == 200

    def test_staff_silence_returns_no_text(self) -> None:
        testbed = ChannelsTestbed()
        business = enable_widget(testbed)
        testbed.pipeline.is_silent = True

        body = (
            testbed.build_http_client()
            .post(
                f"/v1/widget/{business.id}/messages",
                json={"session_key": SESSION_KEY, "text": "Hello?"},
            )
            .json()
        )

        assert body["text"] is None
        assert body["is_handed_off"] is True
        assert body["message_id"] is None
        [visitor_message] = testbed.message_repo.list_by_conversation(
            business.id, testbed.pipeline.conversation_id
        )
        assert body["cursor"] == str(visitor_message.id)

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


def post_message(
    client: Any, business_id: object, session_key: str = SESSION_KEY
) -> Any:
    return client.post(
        f"/v1/widget/{business_id}/messages",
        json={"session_key": session_key, "text": "Hi"},
    )


class TestWidgetMessageRateLimits:
    def test_a_visitor_sending_too_fast_waits_for_the_retry_after(self) -> None:
        testbed = ChannelsTestbed()
        business = enable_widget(testbed)
        client = testbed.build_http_client()

        answers: list[int] = []
        for _ in range(12):
            answers.append(post_message(client, business.id).status_code)
            testbed.clock.advance(5)
        testbed.clock.advance(-5)
        limited = post_message(client, business.id)
        other_visitor = post_message(client, business.id, "v1_another_visitor_77")

        assert answers == [200] * 12
        assert limited.status_code == 429
        assert limited.json()["error"] == "rate_limited"
        # The first message leaves the minute 5 seconds later.
        assert limited.headers["Retry-After"] == "5"
        assert other_visitor.status_code == 200
        assert len(testbed.pipeline.messages) == 13
        testbed.clock.advance(5)
        assert post_message(client, business.id).status_code == 200

    def test_one_address_is_limited_across_visitors(self) -> None:
        testbed = ChannelsTestbed()
        business = enable_widget(testbed)
        client = testbed.build_http_client()

        answers = [
            post_message(
                client, business.id, f"v1_visitor_number_{index:04d}"
            ).status_code
            for index in range(60)
        ]
        limited = post_message(client, business.id, "v1_one_more_visitor_0001")

        assert answers == [200] * 60
        assert limited.status_code == 429
        assert limited.headers["Retry-After"] == "60"
        assert len(testbed.pipeline.messages) == 60


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
