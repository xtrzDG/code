"""
Staff notifications through the platform Telegram bot: staff links and
the bot's webhook.
"""

from base_pydantic_schemas import ImmutableDTO
from typed_time_provider import Microseconds

from app.schemas.constants.channel_events import PlatformBotCommandResult
from app.schemas.dto.channels.channel_webhooks import ChannelWebhookPayload
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.channels.constrained_strings import (
    ManagerLinkCode,
    TelegramBotUsername,
    TelegramDeepLink,
)
from app.schemas.typings.compliance.strings import ClientIpAddress
from app.schemas.typings.handoffs.strings import ManagerName
from app.schemas.typings.localization.constrained_strings import LanguageTag
from app.schemas.typings.users.prefixed_id import UserId


class TelegramLinkRequest(ImmutableDTO):
    """
    HTTP body of a staff Telegram link; without `language` the owner's
    language is used for the staff member's notifications.
    """

    name: ManagerName
    language: LanguageTag | None = None


class CreateTelegramLinkCommand(ImmutableDTO):
    """Owner creates a one-time code that links a staff member's Telegram."""

    user_id: UserId
    business_id: BusinessId
    request: TelegramLinkRequest
    client_ip_address: ClientIpAddress | None = None


class TelegramLinkView(ImmutableDTO):
    """
    One-time link code. The staff member opens `deep_link` (or sends
    "/start <code>" to `bot_username`) before `expires_at`.
    """

    business_id: BusinessId
    code: ManagerLinkCode
    deep_link: TelegramDeepLink | None = None
    bot_username: TelegramBotUsername | None = None
    expires_at: Microseconds


class PlatformBotWebhookRequest(ImmutableDTO):
    """Webhook of the platform Telegram bot that notifies staff."""

    payload: ChannelWebhookPayload


class PlatformBotWebhookSetup(ImmutableDTO):
    """Register the platform bot's webhook with Telegram (deployment step)."""


class PlatformBotWebhookOutcome(ImmutableDTO):
    """How the platform bot handled the update."""

    result: PlatformBotCommandResult
