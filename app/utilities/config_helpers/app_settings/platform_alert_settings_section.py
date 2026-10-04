"""PLATFORM_ALERT_*: where the platform alerts go and how often they repeat."""

from collections.abc import Mapping
from typing import TypedDict

from app.schemas.configurations.platform_alert_settings import (
    DEFAULT_ALERT_COOLDOWN_MINUTES,
    PlatformAlertSettings,
)
from app.schemas.typings.monitoring.constrained_integers import AlertCooldownMinutes
from app.schemas.typings.monitoring.constrained_strings import AlertChatId
from app.schemas.typings.users.constrained_strings import EmailAddress
from app.utilities.config_helpers.app_settings.environment_variable_readers import (
    parse_setting,
    read_integer,
    read_raw_list,
)


class PlatformAlertSettingsSection(TypedDict):
    """The `AppSettings` field of the platform alerts."""

    platform_alerts: PlatformAlertSettings


def read_platform_alert_settings(
    environment_variables: Mapping[str, str],
) -> PlatformAlertSettingsSection:
    return PlatformAlertSettingsSection(
        platform_alerts=PlatformAlertSettings(
            telegram_chat_ids=[
                parse_setting("PLATFORM_ALERT_TELEGRAM_CHAT_IDS", chat_id, AlertChatId)
                for chat_id in read_raw_list(
                    environment_variables, "PLATFORM_ALERT_TELEGRAM_CHAT_IDS"
                )
            ],
            emails=[
                parse_setting("PLATFORM_ALERT_EMAILS", email.lower(), EmailAddress)
                for email in read_raw_list(
                    environment_variables, "PLATFORM_ALERT_EMAILS"
                )
            ],
            cooldown_minutes=parse_setting(
                "PLATFORM_ALERT_COOLDOWN_MINUTES",
                read_integer(
                    environment_variables,
                    "PLATFORM_ALERT_COOLDOWN_MINUTES",
                    DEFAULT_ALERT_COOLDOWN_MINUTES,
                ),
                AlertCooldownMinutes,
            ),
        )
    )
