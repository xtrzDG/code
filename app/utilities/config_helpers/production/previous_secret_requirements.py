"""
The values of webhook secrets in rotation (`<NAME>_PREVIOUS`): optional in
production, but never on their own (a leftover of a rotation whose current
value was removed) and never a published test value.
"""

from app.schemas.configurations.app_settings import AppSettings
from app.schemas.typings.platform.strings import (
    PlatformSecret,
    ProductionSettingProblem,
)

# Flitt's published test key: anyone can sign a callback with it.
FLITT_PUBLISHED_TEST_VALUE: str = "test"


def find_previous_secret_problems(
    settings: AppSettings,
) -> list[ProductionSettingProblem]:
    previous = settings.previous_secrets
    pairs: list[tuple[str, PlatformSecret | None, PlatformSecret | None]] = [
        (
            "ELEVENLABS_WEBHOOK_SECRET",
            settings.elevenlabs_webhook_secret,
            previous.elevenlabs_webhook_secret,
        ),
        ("META_APP_SECRET", settings.meta_app_secret, previous.meta_app_secret),
        ("FLITT_SECRET_KEY", settings.flitt_secret_key, previous.flitt_secret_key),
        (
            "ZADARMA_API_SECRET",
            settings.zadarma_api_secret,
            previous.zadarma_api_secret,
        ),
        ("TWILIO_AUTH_TOKEN", settings.twilio_auth_token, previous.twilio_auth_token),
    ]
    problems: list[ProductionSettingProblem] = [
        ProductionSettingProblem(
            f"{name}_PREVIOUS is set without {name}: a previous value is only "
            f"accepted next to the current one; set {name} or remove "
            f"{name}_PREVIOUS."
        )
        for name, current, previous_value in pairs
        if previous_value is not None and current is None
    ]
    if str(previous.flitt_secret_key or "").strip() == FLITT_PUBLISHED_TEST_VALUE:
        problems.append(
            ProductionSettingProblem(
                "FLITT_SECRET_KEY_PREVIOUS is the test merchant's published key: "
                "anyone could sign a payment notification with it."
            )
        )

    return problems
