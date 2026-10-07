"""Settings, Flitt credentials, clock constants and country presets for billing."""

from dataclasses import dataclass

from app.clients.flitt.flitt_protocol import build_parameter_signature
from app.schemas.configurations.app_settings import AppSettings
from app.utilities.config_helpers.app_settings.app_settings_assembler import (
    assemble_app_settings,
)

# 2026-10-01 09:00 UTC, the concept's date.
START_NANOSECONDS: int = 1_790_845_200_000_000_000
NANOSECONDS_PER_MICROSECOND: int = 1_000
MICROSECONDS_PER_DAY: int = 24 * 60 * 60 * 1_000_000
MICROSECONDS_PER_HOUR: int = 60 * 60 * 1_000_000
FLITT_MERCHANT_ID: str = "1549901"
FLITT_SECRET_KEY: str = "test"
APP_BASE_URL: str = "https://api.assistant.example"
CABINET_ORIGIN: str = "https://app.assistant.example"
CHECKOUT_URL: str = "https://pay.flitt.com/merchants/test/default/index.html?token=t1"


@dataclass(frozen=True)
class CountryPreset:
    """Country defaults a business would get at creation."""

    country_code: str
    currency_code: str
    timezone: str
    owner_language: str
    languages: tuple[str, ...]


GEORGIA = CountryPreset("GE", "GEL", "Asia/Tbilisi", "ka", ("ka", "ru", "en"))
ITALY = CountryPreset("IT", "EUR", "Europe/Rome", "it", ("it", "en"))
USA = CountryPreset("US", "USD", "America/New_York", "en", ("en", "es"))
JAPAN = CountryPreset("JP", "JPY", "Asia/Tokyo", "ja", ("ja", "en"))
ISRAEL = CountryPreset("IL", "ILS", "Asia/Jerusalem", "he", ("he", "ar", "en"))
KAZAKHSTAN = CountryPreset("KZ", "KZT", "Asia/Almaty", "ru", ("kk", "ru"))


def build_settings() -> AppSettings:
    return assemble_app_settings(
        {
            "APP_ENV": "test",
            "APP_BASE_URL": APP_BASE_URL,
            "CORS_ALLOWED_ORIGINS": CABINET_ORIGIN,
            "FLITT_MERCHANT_ID": FLITT_MERCHANT_ID,
            "FLITT_SECRET_KEY": FLITT_SECRET_KEY,
        }
    )


def sign_flitt_callback(parameters: dict[str, object]) -> dict[str, object]:
    signed: dict[str, object] = dict(parameters)
    signed["signature"] = build_parameter_signature(FLITT_SECRET_KEY, signed)
    return signed
