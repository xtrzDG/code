"""Connect a Telegram bot: check its token and set its webhook."""

import re

from app.contracts.channel_clients import TelegramBotApiClientContract
from app.schemas.configurations.app_settings import AppSettings
from app.schemas.constants.channels import ChannelKind
from app.schemas.dto.channels.channel_settings import ConnectChannelRequest
from app.schemas.dto.channels.provider_profiles import TelegramBotProfile
from app.schemas.exceptions.application_errors import (
    ExternalServiceError,
    ValidationFailedError,
)
from app.schemas.typings.channels.constrained_strings import ChannelWebhookUrl
from app.schemas.typings.channels.prefixed_id import ChannelId
from app.schemas.typings.channels.strings import (
    ChannelExternalId,
    ChannelSecret,
    RawChannelSecretInput,
)
from app.schemas.typings.platform.strings import PlatformSecret
from app.use_cases.channels.connection.channel_connection import (
    AccountCheck,
    ChannelConnection,
)
from app.utilities.channels.channel_endpoints import (
    build_telegram_webhook_path,
    join_public_url,
)
from app.utilities.channels.webhook_signatures import derive_telegram_webhook_secret

# Token from @BotFather: "<bot id>:<35 characters>".
TELEGRAM_BOT_TOKEN_PATTERN: re.Pattern[str] = re.compile(
    r"^[0-9]{5,20}:[A-Za-z0-9_\-]{30,100}$"
)


def read_bot_token(raw_token: RawChannelSecretInput | None) -> ChannelSecret:
    """A @BotFather token, checked for shape (spaces around it are ignored)."""

    token_text: str = "" if raw_token is None else raw_token.strip()
    if TELEGRAM_BOT_TOKEN_PATTERN.fullmatch(token_text) is None:
        raise ValidationFailedError(
            "bot_token must be the token @BotFather gave, like 123456789:AA..."
        )

    return ChannelSecret(token_text)


def connect_telegram(
    telegram_client: TelegramBotApiClientContract,
    app_settings: AppSettings,
    require_free_account: AccountCheck,
    channel_id: ChannelId,
    request: ConnectChannelRequest,
) -> ChannelConnection:
    bot_token: ChannelSecret = read_bot_token(request.bot_token)
    encryption_key: PlatformSecret | None = app_settings.encryption_key
    if encryption_key is None:
        raise ExternalServiceError(
            "Telegram cannot be connected: ENCRYPTION_KEY is not configured."
        )

    webhook_url: ChannelWebhookUrl = build_webhook_url(
        app_settings, build_telegram_webhook_path(channel_id)
    )
    profile: TelegramBotProfile = telegram_client.get_me(bot_token)
    external_id = ChannelExternalId(str(profile.username))
    require_free_account(ChannelKind.TELEGRAM, external_id)
    telegram_client.set_webhook(
        bot_token,
        webhook_url,
        derive_telegram_webhook_secret(encryption_key, bot_token),
    )
    return ChannelConnection(external_id=external_id, secret=bot_token)


def build_webhook_url(app_settings: AppSettings, path: str) -> ChannelWebhookUrl:
    base_url = app_settings.app_base_url
    try:
        return ChannelWebhookUrl(
            join_public_url("" if base_url is None else str(base_url), path)
        )
    except ValueError as error:
        raise ExternalServiceError(
            "Webhooks need a public https APP_BASE_URL; it is missing or not https."
        ) from error
