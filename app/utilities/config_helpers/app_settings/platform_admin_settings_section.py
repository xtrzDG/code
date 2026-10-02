"""PLATFORM_ADMIN_*: who signs in as a platform administrator."""

from collections.abc import Mapping
from typing import TypedDict

from app.schemas.typings.localization.constrained_strings import E164PhoneNumber
from app.schemas.typings.users.constrained_strings import EmailAddress
from app.utilities.config_helpers.app_settings.environment_variable_readers import (
    read_raw_list,
)


class PlatformAdminSettingsSection(TypedDict):
    """The `AppSettings` fields naming the platform administrators."""

    platform_admin_emails: list[EmailAddress]
    platform_admin_phone_numbers: list[E164PhoneNumber]


def read_platform_admin_settings(
    environment_variables: Mapping[str, str],
) -> PlatformAdminSettingsSection:
    return PlatformAdminSettingsSection(
        platform_admin_emails=[
            EmailAddress(email.lower())
            for email in read_raw_list(environment_variables, "PLATFORM_ADMIN_EMAILS")
        ],
        platform_admin_phone_numbers=[
            E164PhoneNumber(phone_number)
            for phone_number in read_raw_list(
                environment_variables,
                "PLATFORM_ADMIN_PHONE_NUMBERS",
            )
        ],
    )
