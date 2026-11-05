"""A country's currency, time zones and login code channels."""

from datetime import date

import phonenumbers
from babel.numbers import get_territory_currencies
from phonenumbers import PhoneNumber
from phonenumbers.timezone import time_zones_for_number

from app.registries.localization.curated_country_telephony import (
    TELEGRAM_OTP_COUNTRIES,
    WHATSAPP_FIRST_COUNTRIES,
)
from app.registries.localization.curated_country_time_and_money import (
    CURATED_CURRENCIES,
    CURATED_DEFAULT_TIMEZONES,
    FALLBACK_CURRENCY,
    FALLBACK_TIMEZONE,
)
from app.schemas.constants.localization import OtpDeliveryChannel
from app.schemas.typings.localization.constrained_strings import (
    CountryCode,
    CurrencyCode,
    TimezoneName,
)
from app.utilities.localization.timezones import (
    is_known_timezone_name,
    list_territory_timezone_names,
)

UNKNOWN_TIMEZONE_NAME: str = "Etc/Unknown"


def find_country_currency(
    country_code: CountryCode, currency_date: date
) -> CurrencyCode:
    curated_currency: CurrencyCode | None = CURATED_CURRENCIES.get(country_code)
    if curated_currency is not None:
        return curated_currency

    for currency_code in get_territory_currencies(
        str(country_code),
        start_date=currency_date,
        tender=True,
    ):
        try:
            return CurrencyCode(currency_code)
        except ValueError:
            continue

    return FALLBACK_CURRENCY


def find_country_timezones(region_code: str) -> list[TimezoneName]:
    """CLDR zones of a region; libphonenumber zones where CLDR has none."""

    timezones: list[TimezoneName] = list_territory_timezone_names(region_code)
    if timezones != []:
        return timezones

    example_number: PhoneNumber | None = phonenumbers.example_number(region_code)
    if example_number is not None:
        timezones = [
            TimezoneName(zone_name)
            for zone_name in sorted(set(time_zones_for_number(example_number)))
            if zone_name != UNKNOWN_TIMEZONE_NAME and is_known_timezone_name(zone_name)
        ]

    return timezones if timezones != [] else [FALLBACK_TIMEZONE]


def choose_default_timezone(
    country_code: CountryCode,
    timezones: list[TimezoneName],
) -> TimezoneName:
    curated_timezone: TimezoneName | None = CURATED_DEFAULT_TIMEZONES.get(country_code)
    if curated_timezone is not None and curated_timezone in timezones:
        return curated_timezone

    return timezones[0]


def find_otp_delivery_channels(country_code: CountryCode) -> list[OtpDeliveryChannel]:
    otp_delivery_channels: list[OtpDeliveryChannel] = (
        [OtpDeliveryChannel.WHATSAPP, OtpDeliveryChannel.SMS]
        if country_code in WHATSAPP_FIRST_COUNTRIES
        else [OtpDeliveryChannel.SMS, OtpDeliveryChannel.WHATSAPP]
    )
    if country_code in TELEGRAM_OTP_COUNTRIES:
        otp_delivery_channels.append(OtpDeliveryChannel.TELEGRAM)

    return otp_delivery_channels
