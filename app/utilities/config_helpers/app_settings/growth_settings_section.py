"""
WHATSAPP_WAITLIST_TEMPLATE, WHATSAPP_REBOOKING_TEMPLATE and
SUBSCRIPTION_PAUSE_ENABLED: the revenue features and the seasonal pause.
"""

from collections.abc import Mapping
from typing import TypedDict

from app.schemas.configurations.growth_settings import GrowthSettings
from app.schemas.typings.channels.constrained_strings import WhatsAppTemplateName
from app.utilities.config_helpers.app_settings.environment_variable_readers import (
    optional_text,
    read_boolean,
)


class GrowthSettingsSection(TypedDict):
    """The `AppSettings` field of the waitlist and the rebooking campaigns."""

    growth: GrowthSettings


def read_growth_settings(
    environment_variables: Mapping[str, str],
) -> GrowthSettingsSection:
    """Every variable is optional (see `GrowthSettings`)."""

    return GrowthSettingsSection(
        growth=GrowthSettings(
            waitlist_template_name=optional_text(
                environment_variables,
                "WHATSAPP_WAITLIST_TEMPLATE",
                WhatsAppTemplateName,
            ),
            rebooking_template_name=optional_text(
                environment_variables,
                "WHATSAPP_REBOOKING_TEMPLATE",
                WhatsAppTemplateName,
            ),
            is_subscription_pause_enabled=read_boolean(
                environment_variables, "SUBSCRIPTION_PAUSE_ENABLED", False
            ),
        )
    )
