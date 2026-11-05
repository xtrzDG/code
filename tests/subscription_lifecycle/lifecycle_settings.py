"""The billing testbed's settings with the seasonal pause turned on or off."""

from app.schemas.configurations.app_settings import AppSettings
from app.utilities.config_helpers.app_settings.app_settings_assembler import (
    assemble_app_settings,
)
from tests.billing.billing_settings import (
    APP_BASE_URL,
    CABINET_ORIGIN,
    FLITT_MERCHANT_ID,
    FLITT_SECRET_KEY,
)


def lifecycle_settings(is_pause_enabled: bool) -> AppSettings:
    return assemble_app_settings(
        {
            "APP_ENV": "test",
            "APP_BASE_URL": APP_BASE_URL,
            "CABINET_BASE_URL": CABINET_ORIGIN,
            "CORS_ALLOWED_ORIGINS": CABINET_ORIGIN,
            "FLITT_MERCHANT_ID": FLITT_MERCHANT_ID,
            "FLITT_SECRET_KEY": FLITT_SECRET_KEY,
            "SUBSCRIPTION_PAUSE_ENABLED": "true" if is_pause_enabled else "false",
        }
    )
