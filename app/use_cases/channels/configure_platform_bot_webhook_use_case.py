from app.contracts.channel_clients import TelegramBotApiClientContract
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.configurations.app_settings import AppSettings
from app.schemas.dto.channels import PlatformBotWebhookSetup, TelegramBotProfile
from app.schemas.exceptions.application_errors import ExternalServiceError
from app.schemas.typings.channels.constrained_strings import ChannelWebhookUrl
from app.schemas.typings.platform.strings import PlatformSecret
from app.utilities.channels.channel_endpoints import (
    TELEGRAM_PLATFORM_WEBHOOK_PATH,
    join_public_url,
)
from app.utilities.channels.webhook_signatures import derive_telegram_webhook_secret


class ConfigurePlatformBotWebhookUseCase(
    UseCaseContract[PlatformBotWebhookSetup, TelegramBotProfile]
):
    """
    Point the platform Telegram bot at APP_BASE_URL/v1/channels/
    telegram-platform/webhook with its derived secret token (a deployment
    step; run again after APP_BASE_URL, the bot token or ENCRYPTION_KEY
    change). Returns the bot, whose username goes into staff deep links.
    """

    def __init__(
        self,
        telegram_client: TelegramBotApiClientContract,
        app_settings: AppSettings,
    ) -> None:
        self._telegram_client: TelegramBotApiClientContract = telegram_client
        self._app_settings: AppSettings = app_settings

    def run(self, input_data: PlatformBotWebhookSetup) -> TelegramBotProfile:
        del input_data
        bot_token: PlatformSecret | None = (
            self._app_settings.telegram_platform_bot_token
        )
        encryption_key: PlatformSecret | None = self._app_settings.encryption_key
        base_url = self._app_settings.app_base_url
        if bot_token is None or encryption_key is None or base_url is None:
            raise ExternalServiceError(
                "The platform bot needs TELEGRAM_PLATFORM_BOT_TOKEN, "
                "ENCRYPTION_KEY and APP_BASE_URL."
            )

        try:
            webhook_url = ChannelWebhookUrl(
                join_public_url(str(base_url), TELEGRAM_PLATFORM_WEBHOOK_PATH)
            )
        except ValueError as error:
            raise ExternalServiceError(
                "Telegram webhooks need an https APP_BASE_URL."
            ) from error

        profile: TelegramBotProfile = self._telegram_client.get_me(bot_token)
        self._telegram_client.set_webhook(
            bot_token,
            webhook_url,
            derive_telegram_webhook_secret(encryption_key, bot_token),
        )
        return profile
