"""Connecting WhatsApp, Messenger and Instagram from the cabinet."""

import logging

import pytest

from app.schemas.constants.channels import ChannelKind
from tests.channels.cabinet_setup import (
    INSTAGRAM_ID,
    PAGE_ID,
    PHONE_NUMBER_ID,
    CabinetSetup,
)
from tests.channels.channels_settings import (
    PAGE_ACCESS_TOKEN,
    WHATSAPP_SYSTEM_TOKEN,
    build_settings,
)


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

    def test_whatsapp_without_the_system_user_token_reads_a_plain_text(
        self, caplog: pytest.LogCaptureFixture
    ) -> None:
        unconfigured = CabinetSetup(build_settings(WHATSAPP_SYSTEM_USER_TOKEN=""))

        with caplog.at_level(logging.WARNING):
            response = unconfigured.put("whatsapp", {"phone_number_id": PHONE_NUMBER_ID})

        assert response.status_code == 502
        assert response.json()["message"] == (
            "WhatsApp cannot be connected right now. Contact support."
        )
        assert "WHATSAPP_SYSTEM_USER_TOKEN" in caplog.text
        assert unconfigured.testbed.meta_transport.requests == []

    @pytest.mark.parametrize(
        ("channel", "body", "name"),
        [
            ("whatsapp", {"phone_number_id": PHONE_NUMBER_ID}, "WhatsApp"),
            (
                "messenger",
                {"page_id": PAGE_ID, "page_access_token": PAGE_ACCESS_TOKEN},
                "Messenger",
            ),
            (
                "instagram",
                {"page_id": PAGE_ID, "page_access_token": PAGE_ACCESS_TOKEN},
                "Instagram",
            ),
        ],
    )
    def test_meta_channels_are_refused_without_the_app_secret(
        self,
        caplog: pytest.LogCaptureFixture,
        channel: str,
        body: dict[str, str],
        name: str,
    ) -> None:
        # Without META_APP_SECRET every Meta webhook is refused, so the
        # channel could never receive a message: it is not connected at all.
        setup = CabinetSetup(build_settings(META_APP_SECRET=""))

        with caplog.at_level(logging.WARNING):
            response = setup.put(channel, body)

        assert response.status_code == 502
        assert response.json()["message"] == (
            f"{name} cannot be connected right now. Contact support."
        )
        assert "META_APP_SECRET" in caplog.text
        assert "META_APP_SECRET" not in response.text
        assert setup.testbed.meta_transport.requests == []

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
