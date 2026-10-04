"""SUPPRESSION_LIST_KEY and BUSINESS_EXPORT_LINK_HOURS: data-subject rights."""

from collections.abc import Mapping
from typing import TypedDict

from app.schemas.configurations.privacy_settings import (
    DEFAULT_EXPORT_LINK_HOURS,
    PrivacySettings,
)
from app.schemas.typings.platform.strings import PlatformSecret
from app.schemas.typings.privacy.constrained_integers import ExportLinkLifetimeHours
from app.utilities.config_helpers.app_settings.environment_variable_readers import (
    optional_text,
    parse_setting,
    read_integer,
)


class PrivacySettingsSection(TypedDict):
    """The `AppSettings` field of data-subject rights and exports."""

    privacy: PrivacySettings


def read_privacy_settings(
    environment_variables: Mapping[str, str],
) -> PrivacySettingsSection:
    """Both optional: the key falls back as `PrivacySettings` explains."""

    return PrivacySettingsSection(
        privacy=PrivacySettings(
            suppression_list_key=optional_text(
                environment_variables, "SUPPRESSION_LIST_KEY", PlatformSecret
            ),
            export_link_hours=parse_setting(
                "BUSINESS_EXPORT_LINK_HOURS",
                read_integer(
                    environment_variables,
                    "BUSINESS_EXPORT_LINK_HOURS",
                    DEFAULT_EXPORT_LINK_HOURS,
                ),
                ExportLinkLifetimeHours,
            ),
        )
    )
