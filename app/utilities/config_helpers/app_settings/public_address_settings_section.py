"""APP_BASE_URL and CABINET_BASE_URL: where the API and the cabinet are reached."""

from collections.abc import Mapping
from typing import TypedDict

from app.schemas.typings.channels.constrained_strings import PublicBaseUrl
from app.schemas.typings.platform.constrained_strings import CabinetBaseUrl
from app.utilities.config_helpers.app_settings.environment_variable_readers import (
    optional_text,
)

# The cabinet's development server (web/README.md, `npm run dev`).
DEVELOPMENT_CABINET_BASE_URL: str = "http://localhost:3000"


class PublicAddressSettingsSection(TypedDict):
    """The `AppSettings` fields of the public addresses."""

    app_base_url: PublicBaseUrl | None
    cabinet_base_url: CabinetBaseUrl | None


def read_public_address_settings(
    environment_variables: Mapping[str, str],
    is_development: bool,
) -> PublicAddressSettingsSection:
    return PublicAddressSettingsSection(
        app_base_url=optional_text(
            environment_variables,
            "APP_BASE_URL",
            PublicBaseUrl,
        ),
        cabinet_base_url=read_cabinet_base_url(environment_variables, is_development),
    )


def read_cabinet_base_url(
    environment_variables: Mapping[str, str],
    is_development: bool,
) -> CabinetBaseUrl | None:
    """
    CABINET_BASE_URL, the owner cabinet's public address (without a trailing
    slash). Development and tests default to the cabinet's development
    server; production has no default.
    """

    raw_value: str = environment_variables.get("CABINET_BASE_URL", "").strip()
    if raw_value != "":
        return CabinetBaseUrl(raw_value.rstrip("/"))

    return CabinetBaseUrl(DEVELOPMENT_CABINET_BASE_URL) if is_development else None
