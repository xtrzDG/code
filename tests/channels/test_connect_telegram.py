"""Connecting a Telegram bot from the cabinet."""

from typing import Any

import httpx
import pytest

from app.schemas.constants.channels import ChannelKind, ChannelStatus
from app.schemas.typings.channels.strings import ChannelSecret
from app.schemas.typings.platform.strings import PlatformSecret
from app.utilities.channels.delivery_targets import find_business_channel
from app.utilities.channels.webhook_signatures import derive_telegram_webhook_secret
from tests.channels.cabinet_setup import CabinetSetup
from tests.channels.channels_settings import (
    ENCRYPTION_KEY,
    TELEGRAM_BOT_TOKEN,
    build_settings,
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

        assert (response.status_code, response.content) == (204, b"")
        stored = setup.stored(ChannelKind.TELEGRAM)
        assert stored.status is ChannelStatus.DISABLED
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

        assert setup.delete("telegram").status_code == 204
        assert setup.stored(ChannelKind.TELEGRAM).status is ChannelStatus.DISABLED
