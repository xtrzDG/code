"""Linking staff to the platform bot and setting the bot up."""

import httpx
import pytest

from app.schemas.dto.channels.staff_links import PlatformBotWebhookSetup
from app.schemas.exceptions.application_errors import ExternalServiceError
from app.use_cases.channels.configure_platform_bot_webhook_use_case import (
    ConfigurePlatformBotWebhookUseCase,
)
from tests.channels.channels_payloads import telegram_ok
from tests.channels.channels_settings import build_settings
from tests.channels.platform_bot_setup import PLATFORM_SECRET, PlatformBotSetup
from tests.channels.testbed import ChannelsTestbed


class TestTelegramLinkCreation:
    def test_owner_gets_a_one_time_code_and_deep_link(self) -> None:
        setup = PlatformBotSetup()

        response = setup.create_link({"name": "Levan"})

        assert response.status_code == 201
        body = response.json()
        code: str = body["code"]
        assert len(code) == 10
        assert body["bot_username"] == "workshop_staff_bot"
        assert body["deep_link"] == f"https://t.me/workshop_staff_bot?start={code}"
        assert (
            body["expires_at"] == setup.testbed.clock.now_microseconds() + 1_800_000_000
        )
        [link] = setup.testbed.link_repo.list_by_business(setup.business.id)
        assert link.language == "ru"
        assert code not in str(link.code_hash)

    def test_staff_cannot_create_links_and_input_is_checked(self) -> None:
        setup = PlatformBotSetup()

        assert setup.create_link({"name": "Levan"}, token="staff").status_code == 403
        assert setup.create_link({"name": "   "}).status_code == 422
        assert setup.create_link({"name": "x" * 101}).status_code == 422
        assert setup.create_link({"name": "Levan", "language": "xx"}).status_code == 422

    def test_without_the_platform_bot_nothing_is_created(self) -> None:
        setup = PlatformBotSetup(build_settings(TELEGRAM_PLATFORM_BOT_TOKEN=""))

        assert setup.create_link({"name": "Levan"}).status_code == 502
        assert setup.testbed.link_repo.list_by_business(setup.business.id) == []

    def test_unreachable_bot_still_gives_the_code(self) -> None:
        setup = PlatformBotSetup()
        setup.testbed.telegram_transport.failure = httpx.ConnectError("down")

        body = setup.create_link({"name": "Levan"}).json()

        assert body["deep_link"] is None
        assert len(body["code"]) == 10


class TestPlatformBotSetup:
    def test_webhook_is_registered_with_the_derived_secret(self) -> None:
        testbed = ChannelsTestbed()
        testbed.telegram_transport.respond(
            "POST", r"/getMe$", telegram_ok({"username": "workshop_staff_bot"})
        )
        testbed.telegram_transport.respond("POST", r"/setWebhook$", telegram_ok())

        profile = ConfigurePlatformBotWebhookUseCase(
            testbed.telegram_client, testbed.settings
        ).run(PlatformBotWebhookSetup())

        assert profile.username == "workshop_staff_bot"
        [request] = testbed.telegram_transport.requests_to("/setWebhook")
        assert request.json()["url"] == (
            "https://api.workshop.test/v1/channels/telegram-platform/webhook"
        )
        assert request.json()["secret_token"] == PLATFORM_SECRET

    def test_missing_settings_are_reported(self) -> None:
        for overrides in (
            {"TELEGRAM_PLATFORM_BOT_TOKEN": ""},
            {"APP_BASE_URL": ""},
            {"APP_BASE_URL": "http://localhost:8000"},
        ):
            testbed = ChannelsTestbed(build_settings(**overrides))
            testbed.telegram_transport.respond(
                "POST", r"/getMe$", telegram_ok({"username": "bot_name"})
            )
            with pytest.raises(ExternalServiceError):
                ConfigurePlatformBotWebhookUseCase(
                    testbed.telegram_client, testbed.settings
                ).run(PlatformBotWebhookSetup())
