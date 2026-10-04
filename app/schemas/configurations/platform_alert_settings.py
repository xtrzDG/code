from base_pydantic_schemas import ImmutableDTO
from pydantic import Field

from app.schemas.typings.monitoring.constrained_integers import AlertCooldownMinutes
from app.schemas.typings.monitoring.constrained_strings import AlertChatId
from app.schemas.typings.users.constrained_strings import EmailAddress

DEFAULT_ALERT_COOLDOWN_MINUTES: int = 60


class PlatformAlertSettings(ImmutableDTO):
    """
    Where the platform alerts go (docs/operations/slo.md): the Telegram
    chats the platform bot posts them to (PLATFORM_ALERT_TELEGRAM_CHAT_IDS,
    an ops group with the bot as a member; needs
    TELEGRAM_PLATFORM_BOT_TOKEN) and the e-mail addresses that get them too
    (PLATFORM_ALERT_EMAILS, over SMTP). Without either, the alerts are
    still checked, logged and shown on the admin system page. A firing
    alert is sent again after PLATFORM_ALERT_COOLDOWN_MINUTES while it
    still fires.
    """

    telegram_chat_ids: list[AlertChatId] = Field(default_factory=list[AlertChatId])
    emails: list[EmailAddress] = Field(default_factory=list[EmailAddress])
    cooldown_minutes: AlertCooldownMinutes = AlertCooldownMinutes(
        DEFAULT_ALERT_COOLDOWN_MINUTES
    )
