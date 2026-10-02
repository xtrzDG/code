"""Settings, platform secrets and country defaults of the channels tests."""

from dataclasses import dataclass

from app.schemas.configurations.app_settings import AppSettings
from app.utilities.config_helpers.app_settings.app_settings_assembler import (
    assemble_app_settings,
)

APP_BASE_URL: str = "https://api.workshop.test"
META_APP_SECRET: str = "meta-app-secret-for-tests"
META_VERIFY_TOKEN: str = "meta-verify-token-for-tests"
WHATSAPP_SYSTEM_TOKEN: str = "whatsapp-system-user-token"
PLATFORM_BOT_TOKEN: str = "700000001:PLATFORMbotTOKENfortestsPLATFORMbotTOKEN"
ELEVENLABS_WEBHOOK_SECRET: str = "elevenlabs-webhook-secret-for-tests"
ENCRYPTION_KEY: str = "an-encryption-key-that-is-long-enough-for-tests"
TELEGRAM_BOT_TOKEN: str = "123456789:AAHdqTcvCH1vGWJxfSeofSAs0K5PALDsaw"
OTHER_TELEGRAM_BOT_TOKEN: str = "987654321:BBHdqTcvCH1vGWJxfSeofSAs0K5PALDsbx"
PAGE_ACCESS_TOKEN: str = "EAAGpageAccessTokenForTests0123456789"

TEST_ENVIRONMENT: dict[str, str] = {
    "APP_ENV": "test",
    "APP_BASE_URL": APP_BASE_URL,
    "ENCRYPTION_KEY": ENCRYPTION_KEY,
    "META_APP_SECRET": META_APP_SECRET,
    "META_VERIFY_TOKEN": META_VERIFY_TOKEN,
    "WHATSAPP_SYSTEM_USER_TOKEN": WHATSAPP_SYSTEM_TOKEN,
    "WHATSAPP_NOTIFICATION_PHONE_NUMBER_ID": "900000000000001",
    "WHATSAPP_NOTIFICATION_TEMPLATE": "staff_notification",
    "TELEGRAM_PLATFORM_BOT_TOKEN": PLATFORM_BOT_TOKEN,
    "ELEVENLABS_API_KEY": "elevenlabs-api-key",
    "ELEVENLABS_WEBHOOK_SECRET": ELEVENLABS_WEBHOOK_SECRET,
}


def build_settings(**overrides: str) -> AppSettings:
    """Test settings; an override with an empty value removes the variable."""

    environment: dict[str, str] = {**TEST_ENVIRONMENT, **overrides}
    return assemble_app_settings(
        {name: value for name, value in environment.items() if value != ""}
    )


@dataclass(frozen=True)
class CountrySetup:
    """Defaults of a business in one country (taken from its country profile)."""

    country_code: str
    timezone: str
    currency_code: str
    languages: tuple[str, ...]


GEORGIA = CountrySetup("GE", "Asia/Tbilisi", "GEL", ("ka", "ru", "en"))
ISRAEL = CountrySetup("IL", "Asia/Jerusalem", "ILS", ("he", "ar", "en"))
POLAND = CountrySetup("PL", "Europe/Warsaw", "PLN", ("pl", "en"))
BRAZIL = CountrySetup("BR", "America/Sao_Paulo", "BRL", ("pt-BR", "en"))
KAZAKHSTAN = CountrySetup("KZ", "Asia/Almaty", "KZT", ("kk", "ru", "en"))
ARMENIA = CountrySetup("AM", "Asia/Yerevan", "AMD", ("hy", "ru", "en"))
UNITED_STATES = CountrySetup("US", "America/New_York", "USD", ("en", "es"))
