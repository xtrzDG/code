"""SUPPRESSION_LIST_KEY and EXPORT_DOWNLOAD_LINK_MINUTES: data-subject rights."""

from collections.abc import Mapping
from typing import TypedDict

from app.schemas.configurations.privacy_settings import (
    DEFAULT_EXPORT_DOWNLOAD_LINK_MINUTES,
    PrivacySettings,
)
from app.schemas.typings.platform.strings import PlatformSecret
from app.schemas.typings.privacy.constrained_integers import ExportDownloadLinkMinutes
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
            export_download_link_minutes=parse_setting(
                "EXPORT_DOWNLOAD_LINK_MINUTES",
                read_integer(
                    environment_variables,
                    "EXPORT_DOWNLOAD_LINK_MINUTES",
                    DEFAULT_EXPORT_DOWNLOAD_LINK_MINUTES,
                ),
                ExportDownloadLinkMinutes,
            ),
        )
    )
