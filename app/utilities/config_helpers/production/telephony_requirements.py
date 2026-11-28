"""
Rented phone numbers in production: PHONE_NUMBER_PROVIDER=twilio needs the
Twilio account (TWILIO_ACCOUNT_SID and TWILIO_AUTH_TOKEN), which buys the
numbers and signs their call fallback, and ELEVENLABS_API_KEY, with which
the voice platform imports them. Without one of them the cabinet would
quietly tell every owner to ask the team for a number. An SMS sender is
not needed: numbers and calls work without it (SMS is then off).
"""

from app.schemas.configurations.app_settings import AppSettings
from app.schemas.constants.phone_numbers import PhoneNumberProvider
from app.schemas.typings.platform.strings import ProductionSettingProblem


def find_telephony_problems(settings: AppSettings) -> list[ProductionSettingProblem]:
    if settings.phone_numbers.provider is not PhoneNumberProvider.TWILIO:
        return []

    missing: list[str] = [
        name
        for name, value in (
            ("TWILIO_ACCOUNT_SID", settings.twilio_account_sid),
            ("TWILIO_AUTH_TOKEN", settings.twilio_auth_token),
            ("ELEVENLABS_API_KEY", settings.elevenlabs_api_key),
        )
        if value is None
    ]
    if not missing:
        return []

    *others, last = missing
    listed: str = f"{', '.join(others)} and {last}" if others else last
    return [
        ProductionSettingProblem(
            f"PHONE_NUMBER_PROVIDER=twilio needs {listed}, which "
            f"{'are' if others else 'is'} not set: numbers are rented with the "
            "Twilio account (TWILIO_ACCOUNT_SID and TWILIO_AUTH_TOKEN) and "
            "imported into the voice platform with ELEVENLABS_API_KEY, and "
            "without them every owner is told to ask the team for a number. "
            "Set them, or leave PHONE_NUMBER_PROVIDER empty."
        )
    ]
