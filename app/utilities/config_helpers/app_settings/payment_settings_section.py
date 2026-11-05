"""STRIPE_SECRET_KEY and STRIPE_WEBHOOK_SECRET."""

from collections.abc import Mapping
from typing import TypedDict

from app.schemas.configurations.payment_settings import PaymentSettings
from app.schemas.typings.platform.strings import PlatformSecret
from app.utilities.config_helpers.app_settings.environment_variable_readers import (
    optional_text,
)


class PaymentSettingsSection(TypedDict):
    """The `AppSettings` field of Stripe."""

    payments: PaymentSettings


def read_payment_settings(
    environment_variables: Mapping[str, str],
) -> PaymentSettingsSection:
    """Both variables are optional (see `PaymentSettings`)."""

    return PaymentSettingsSection(
        payments=PaymentSettings(
            stripe_secret_key=optional_text(
                environment_variables, "STRIPE_SECRET_KEY", PlatformSecret
            ),
            stripe_webhook_secret=optional_text(
                environment_variables, "STRIPE_WEBHOOK_SECRET", PlatformSecret
            ),
        )
    )
