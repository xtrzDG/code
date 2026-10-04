"""Checking a @BotFather token before the Telegram channel is connected."""

from base_pydantic_schemas import ImmutableDTO
from pydantic import Field

from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.channels.constrained_strings import (
    TelegramBotAvatarDataUrl,
    TelegramBotUsername,
)
from app.schemas.typings.channels.strings import (
    RawChannelSecretInput,
    TelegramBotDisplayName,
)
from app.schemas.typings.users.prefixed_id import UserId


class TelegramTokenCheckRequest(ImmutableDTO):
    """HTTP body: the token @BotFather gave, as pasted (it is not saved)."""

    bot_token: RawChannelSecretInput = Field(repr=False)


class ValidateTelegramTokenCommand(ImmutableDTO):
    """An owner asks Telegram which bot a token belongs to, saving nothing."""

    user_id: UserId
    business_id: BusinessId
    request: TelegramTokenCheckRequest


class TelegramBotCheckView(ImmutableDTO):
    """
    The bot a token opens, as customers will see it: its username, its name
    and its profile photo (a small image inlined as a data URL; None when
    the bot has none or Telegram did not hand it out).
    """

    username: TelegramBotUsername
    display_name: TelegramBotDisplayName | None = None
    avatar_data_url: TelegramBotAvatarDataUrl | None = None
