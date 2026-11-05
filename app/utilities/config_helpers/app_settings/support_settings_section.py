"""SUPPORT_*: how owners reach the platform's support from the cabinet."""

from collections.abc import Mapping
from typing import TypedDict

from app.schemas.configurations.support_settings import SupportSettings
from app.schemas.typings.help.constrained_strings import SupportTelegramUsername
from app.schemas.typings.localization.constrained_strings import E164PhoneNumber
from app.schemas.typings.users.constrained_strings import EmailAddress
from app.utilities.config_helpers.app_settings.environment_variable_readers import (
    parse_setting,
)


class SupportSettingsSection(TypedDict):
    """The `AppSettings` field of the support contacts."""

    support: SupportSettings


def read_support_settings(
    environment_variables: Mapping[str, str],
) -> SupportSettingsSection:
    whatsapp: str = "".join(
        environment_variables.get("SUPPORT_WHATSAPP", "").split()
    ).replace("-", "")
    telegram: str = environment_variables.get("SUPPORT_TELEGRAM", "").strip()
    email: str = environment_variables.get("SUPPORT_EMAIL", "").strip().lower()
    return SupportSettingsSection(
        support=SupportSettings(
            whatsapp_number=(
                parse_setting("SUPPORT_WHATSAPP", whatsapp, E164PhoneNumber)
                if whatsapp
                else None
            ),
            telegram_username=(
                parse_setting(
                    "SUPPORT_TELEGRAM",
                    telegram.removeprefix("@"),
                    SupportTelegramUsername,
                )
                if telegram
                else None
            ),
            email=parse_setting("SUPPORT_EMAIL", email, EmailAddress)
            if email
            else None,
        )
    )
