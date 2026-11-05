"""PHONE_NUMBER_*: numbers the platform rents for businesses from the cabinet."""

from collections.abc import Mapping
from typing import TypedDict

from app.schemas.configurations.phone_number_settings import PhoneNumberSettings
from app.schemas.constants.phone_numbers import PhoneNumberProvider
from app.schemas.typings.telephony.constrained_integers import (
    PhoneNumberPriceMarkupPercent,
)
from app.utilities.config_helpers.app_settings.environment_variable_readers import (
    parse_setting,
    read_integer,
)

DEFAULT_MARKUP_PERCENT: int = 30


class PhoneNumberSettingsSection(TypedDict):
    """The `AppSettings` field of rented phone numbers."""

    phone_numbers: PhoneNumberSettings


def read_phone_number_settings(
    environment_variables: Mapping[str, str],
) -> PhoneNumberSettingsSection:
    """Both variables are optional (see `PhoneNumberSettings`)."""

    provider: str = environment_variables.get("PHONE_NUMBER_PROVIDER", "").strip()
    return PhoneNumberSettingsSection(
        phone_numbers=PhoneNumberSettings(
            provider=(
                parse_setting(
                    "PHONE_NUMBER_PROVIDER", provider.lower(), PhoneNumberProvider
                )
                if provider
                else None
            ),
            price_markup_percent=parse_setting(
                "PHONE_NUMBER_PRICE_MARKUP_PERCENT",
                read_integer(
                    environment_variables,
                    "PHONE_NUMBER_PRICE_MARKUP_PERCENT",
                    DEFAULT_MARKUP_PERCENT,
                ),
                PhoneNumberPriceMarkupPercent,
            ),
        )
    )
