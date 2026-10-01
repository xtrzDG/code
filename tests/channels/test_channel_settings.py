from typing import Any

import httpx
import pytest

from app.schemas.constants.channels import ChannelKind, ChannelStatus
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.domain.channels import ChannelDocument
from app.schemas.typings.channels.strings import ChannelSecret
from app.schemas.typings.localization.constrained_strings import CountryCode
from app.schemas.typings.platform.strings import PlatformSecret
from app.utilities.channels.delivery_targets import find_business_channel
from app.utilities.channels.webhook_signatures import derive_telegram_webhook_secret
from tests.channels.testbed import (
    BRAZIL,
    ENCRYPTION_KEY,
    PAGE_ACCESS_TOKEN,
    TELEGRAM_BOT_TOKEN,
    UNITED_STATES,
    WHATSAPP_SYSTEM_TOKEN,
    ChannelsTestbed,
    HttpResponse,
    bearer,
    build_settings,
    telegram_ok,
)

PAGE_ID: str = "4410001"
INSTAGRAM_ID: str = "17841400000000001"
PHONE_NUMBER_ID: str = "106540352242922"


class CabinetSetup:
    def __init__(self, settings: Any = None) -> None:
        self.testbed = ChannelsTestbed(settings)
        self.owner_id = self.testbed.add_user("owner")
        self.staff_id = self.testbed.add_user("staff")
        self.testbed.add_user("stranger")
        self.business: BusinessDocument = self.testbed.add_business(
            self.owner_id, staff_ids=[self.staff_id]
        )
        self.client = self.testbed.build_http_client()

    def put(
        self, channel: str, body: dict[str, Any], token: str = "owner"
    ) -> HttpResponse:
        return self.client.put(
            f"/v1/businesses/{self.business.id}/channels/{channel}",
            json=body,
            headers=bearer(token),
        )

    def delete(self, channel: str, token: str = "owner") -> HttpResponse:
        return self.client.delete(
            f"/v1/businesses/{self.business.id}/channels/{channel}",
            headers=bearer(token),
        )

    def stored(self, kind: ChannelKind) -> ChannelDocument:
        channel = find_business_channel(
            self.testbed.channel_repo, self.business.id, kind
        )
        assert channel is not None
        return channel

    def script_telegram(self, username: str = "funicular_vr_bot") -> None:
        transport = self.testbed.telegram_transport
        transport.respond("POST", r"/getMe$", telegram_ok({"username": username}))
        transport.respond("POST", r"/setWebhook$", telegram_ok())
        transport.respond("POST", r"/deleteWebhook$", telegram_ok())

    def script_page(self, with_instagram: bool = True) -> None:
        page: dict[str, Any] = {"id": PAGE_ID, "name": "Funicular VR"}
        if with_instagram:
            page["instagram_business_account"] = {"id": INSTAGRAM_ID}
        self.testbed.meta_transport.respond("GET", rf"/{PAGE_ID}$", page)
        self.testbed.meta_transport.respond(
            "POST", rf"/{PAGE_ID}/subscribed_apps$", {"success": True}
        )


class TestConnectTelegram:
    def test_owner_connects_a_bot(self) -> None:
        setup = CabinetSetup()
        setup.script_telegram()

        response = setup.put("telegram", {"bot_token": f"  {TELEGRAM_BOT_TOKEN}\n"})

        assert response.status_code == 200
        view = response.json()
        assert view["channel"] == "telegram"
        assert view["status"] == "connected"
        assert view["account_id"] == "funicular_vr_bot"
        assert view["has_credential"] is True
        assert TELEGRAM_BOT_TOKEN not in response.text
        stored = setup.stored(ChannelKind.TELEGRAM)
        assert stored.encrypted_secret is not None
        assert TELEGRAM_BOT_TOKEN not in str(stored.encrypted_secret)
        assert (
            setup.testbed.secret_cipher.decrypt(stored.encrypted_secret)
            == TELEGRAM_BOT_TOKEN
        )
        [set_webhook] = setup.testbed.telegram_transport.requests_to("/setWebhook")
        assert set_webhook.json()["url"] == (
            f"https://api.workshop.test/v1/channels/telegram/{stored.id}/webhook"
        )
        assert set_webhook.json()["secret_token"] == derive_telegram_webhook_secret(
            PlatformSecret(ENCRYPTION_KEY), ChannelSecret(TELEGRAM_BOT_TOKEN)
        )
        assert ("create", "channel") in setup.testbed.audit_actions(setup.business.id)

    @pytest.mark.parametrize(
        "body",
        [{}, {"bot_token": "not-a-token"}, {"bot_token": "123:short"}],
    )
    def test_malformed_tokens_are_refused_before_calling_telegram(
        self, body: dict[str, Any]
    ) -> None:
        setup = CabinetSetup()

        assert setup.put("telegram", body).status_code == 422
        assert setup.testbed.telegram_transport.requests == []

    def test_token_rejected_by_telegram(self) -> None:
        setup = CabinetSetup()
        setup.testbed.telegram_transport.respond(
            "POST",
            r"/getMe$",
            {"ok": False, "error_code": 401, "description": "Unauthorized"},
            status_code=401,
        )

        response = setup.put("telegram", {"bot_token": TELEGRAM_BOT_TOKEN})

        assert response.status_code == 422
        assert (
            find_business_channel(
                setup.testbed.channel_repo, setup.business.id, ChannelKind.TELEGRAM
            )
            is None
        )

    def test_webhooks_need_an_https_base_url_and_an_encryption_key(self) -> None:
        for overrides in (
            {"APP_BASE_URL": "http://localhost:8000"},
            {"ENCRYPTION_KEY": ""},
        ):
            setup = CabinetSetup(build_settings(**overrides))
            setup.script_telegram()
            assert (
                setup.put("telegram", {"bot_token": TELEGRAM_BOT_TOKEN}).status_code
                == 502
            )
            assert setup.testbed.telegram_transport.requests_to("/setWebhook") == []

    def test_bot_of_another_business_is_refused(self) -> None:
        setup = CabinetSetup()
        setup.script_telegram()
        other_owner = setup.testbed.add_user("other")
        other_business = setup.testbed.add_business(other_owner, name="Other")
        setup.testbed.add_channel(
            other_business.id,
            ChannelKind.TELEGRAM,
            "funicular_vr_bot",
            TELEGRAM_BOT_TOKEN,
        )

        response = setup.put("telegram", {"bot_token": TELEGRAM_BOT_TOKEN})

        assert response.status_code == 409
        assert setup.testbed.telegram_transport.requests_to("/setWebhook") == []

    def test_reconnecting_keeps_one_channel_and_disabling_erases_the_token(
        self,
    ) -> None:
        setup = CabinetSetup()
        setup.script_telegram()
        first = setup.put("telegram", {"bot_token": TELEGRAM_BOT_TOKEN}).json()
        second = setup.put("telegram", {"bot_token": TELEGRAM_BOT_TOKEN}).json()
        assert first["id"] == second["id"]

        response = setup.delete("telegram")

        assert response.status_code == 200
        assert response.json()["status"] == "disabled"
        assert response.json()["has_credential"] is False
        assert response.json()["account_id"] is None
        stored = setup.stored(ChannelKind.TELEGRAM)
        assert stored.encrypted_secret is None and stored.external_id is None
        [delete_webhook] = setup.testbed.telegram_transport.requests_to(
            "/deleteWebhook"
        )
        assert TELEGRAM_BOT_TOKEN in delete_webhook.path
        assert setup.testbed.audit_actions(setup.business.id) == [
            ("create", "channel"),
            ("update", "channel"),
            ("delete", "channel"),
        ]

    def test_disabling_works_when_telegram_is_unreachable(self) -> None:
        setup = CabinetSetup()
        setup.script_telegram()
        setup.put("telegram", {"bot_token": TELEGRAM_BOT_TOKEN})
        setup.testbed.telegram_transport.failure = httpx.ConnectError("down")

        assert setup.delete("telegram").json()["status"] == "disabled"


class TestConnectMetaChannels:
    def test_whatsapp_number_from_embedded_signup(self) -> None:
        setup = CabinetSetup()
        meta = setup.testbed.meta_transport
        meta.respond(
            "GET",
            rf"/{PHONE_NUMBER_ID}$",
            {"id": PHONE_NUMBER_ID, "display_phone_number": "+995 32 200 00 00"},
        )
        meta.respond("POST", r"/555/subscribed_apps$", {"success": True})

        response = setup.put(
            "whatsapp",
            {"phone_number_id": PHONE_NUMBER_ID, "whatsapp_business_account_id": "555"},
        )

        assert response.status_code == 200
        assert response.json()["account_id"] == PHONE_NUMBER_ID
        assert response.json()["has_credential"] is False
        assert [request.path for request in meta.requests] == [
            f"/v23.0/{PHONE_NUMBER_ID}",
            "/v23.0/555/subscribed_apps",
        ]
        assert all(
            request.headers["Authorization"] == f"Bearer {WHATSAPP_SYSTEM_TOKEN}"
            for request in meta.requests
        )

    def test_whatsapp_errors(self) -> None:
        setup = CabinetSetup()
        assert setup.put("whatsapp", {}).status_code == 422
        assert setup.put("whatsapp", {"phone_number_id": "12ab"}).status_code == 422
        setup.testbed.meta_transport.respond(
            "GET",
            rf"/{PHONE_NUMBER_ID}$",
            {"error": {"message": "Unsupported get request", "code": 100}},
            status_code=400,
        )
        assert (
            setup.put("whatsapp", {"phone_number_id": PHONE_NUMBER_ID}).status_code
            == 422
        )

        unconfigured = CabinetSetup(build_settings(WHATSAPP_SYSTEM_USER_TOKEN=""))
        assert (
            unconfigured.put(
                "whatsapp", {"phone_number_id": PHONE_NUMBER_ID}
            ).status_code
            == 502
        )

    def test_messenger_page_and_instagram_account(self) -> None:
        setup = CabinetSetup()
        setup.script_page()
        body = {"page_id": PAGE_ID, "page_access_token": PAGE_ACCESS_TOKEN}

        messenger = setup.put("messenger", body).json()
        instagram = setup.put("instagram", body).json()

        assert messenger["account_id"] == PAGE_ID
        assert instagram["account_id"] == INSTAGRAM_ID
        encrypted_token = setup.stored(ChannelKind.INSTAGRAM).encrypted_secret
        assert encrypted_token is not None
        assert setup.testbed.secret_cipher.decrypt(encrypted_token) == PAGE_ACCESS_TOKEN
        subscriptions = setup.testbed.meta_transport.requests_to("/subscribed_apps")
        assert len(subscriptions) == 2
        assert subscriptions[0].url.params["subscribed_fields"] == (
            "messages,messaging_postbacks"
        )

    def test_page_without_instagram_and_bad_tokens(self) -> None:
        setup = CabinetSetup()
        setup.script_page(with_instagram=False)

        no_instagram = setup.put(
            "instagram", {"page_id": PAGE_ID, "page_access_token": PAGE_ACCESS_TOKEN}
        )
        no_token = setup.put("messenger", {"page_id": PAGE_ID})
        spaces = setup.put(
            "messenger",
            {"page_id": PAGE_ID, "page_access_token": "has a space inside it!"},
        )
        no_page = setup.put("messenger", {"page_access_token": PAGE_ACCESS_TOKEN})

        assert no_instagram.status_code == 422
        assert "Instagram" in no_instagram.json()["message"]
        assert {no_token.status_code, spaces.status_code, no_page.status_code} == {422}


class TestConnectPhoneAndWeb:
    @pytest.mark.parametrize(
        ("country", "typed_number", "expected"),
        [
            (BRAZIL, "(11) 96123-4567", "+5511961234567"),
            (UNITED_STATES, "(202) 555-0123", "+12025550123"),
        ],
    )
    def test_assistant_line_in_the_business_country(
        self, country: Any, typed_number: str, expected: str
    ) -> None:
        setup = CabinetSetup()
        setup.business.country_code = CountryCode(country.country_code)
        setup.testbed.business_repo.save(setup.business)

        response = setup.put("phone", {"phone_number": typed_number})

        assert response.status_code == 200
        assert response.json()["account_id"] == expected

    def test_international_number_and_country_hint(self) -> None:
        setup = CabinetSetup()
        hinted = setup.put(
            "phone", {"phone_number": "0 32 200 00 00", "country_hint": "GE"}
        )
        assert hinted.json()["account_id"] == "+995322000000"

        conflict_setup = CabinetSetup()
        other_owner = conflict_setup.testbed.add_user("other")
        other = conflict_setup.testbed.add_business(other_owner, name="Other")
        conflict_setup.testbed.add_channel(other.id, ChannelKind.PHONE, "+995322000000")
        assert (
            conflict_setup.put(
                "phone", {"phone_number": "+995 32 200 00 00"}
            ).status_code
            == 409
        )
        assert conflict_setup.put("phone", {"phone_number": "12345"}).status_code == 422
        assert conflict_setup.put("phone", {}).status_code == 422

    def test_web_chat_by_its_short_name(self) -> None:
        setup = CabinetSetup()

        response = setup.put("web", {})

        assert response.status_code == 200
        assert response.json()["channel"] == "web_chat"
        assert setup.stored(ChannelKind.WEB_CHAT).status is ChannelStatus.CONNECTED
        assert setup.delete("web_chat").json()["status"] == "disabled"


class TestChannelAccess:
    def test_only_owners_change_channels(self) -> None:
        setup = CabinetSetup()

        assert setup.put("web", {}, token="staff").status_code == 403
        assert setup.put("web", {}, token="stranger").status_code == 404
        assert setup.delete("web", token="staff").status_code == 403

    def test_unknown_and_unsupported_channels(self) -> None:
        setup = CabinetSetup()

        assert setup.put("fax", {}).status_code == 404
        assert setup.put("viber", {}).status_code == 422
        assert setup.put("owner_test", {}).status_code == 422
        assert setup.delete("telegram").status_code == 404

    def test_members_list_channels_without_secrets(self) -> None:
        setup = CabinetSetup()
        setup.testbed.add_channel(setup.business.id, ChannelKind.WEB_CHAT)
        setup.testbed.add_channel(
            setup.business.id, ChannelKind.INSTAGRAM, INSTAGRAM_ID, PAGE_ACCESS_TOKEN
        )
        setup.testbed.add_channel(
            setup.business.id,
            ChannelKind.TELEGRAM,
            "funicular_vr_bot",
            TELEGRAM_BOT_TOKEN,
        )
        other_owner = setup.testbed.add_user("other")
        other = setup.testbed.add_business(other_owner, name="Other")
        setup.testbed.add_channel(other.id, ChannelKind.WHATSAPP, PHONE_NUMBER_ID)

        response = setup.client.get(
            f"/v1/businesses/{setup.business.id}/channels", headers=bearer("staff")
        )

        assert response.status_code == 200
        assert [item["channel"] for item in response.json()] == [
            "telegram",
            "instagram",
            "web_chat",
        ]
        assert PAGE_ACCESS_TOKEN not in response.text
        assert TELEGRAM_BOT_TOKEN not in response.text
        assert "encrypted_secret" not in response.text
        assert (
            setup.client.get(
                f"/v1/businesses/{setup.business.id}/channels",
                headers=bearer("stranger"),
            ).status_code
            == 404
        )
