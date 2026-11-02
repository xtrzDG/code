"""<NAME>_PREVIOUS: the values of rotated webhook secrets still accepted."""

from collections.abc import Mapping
from typing import TypedDict

from app.schemas.configurations.previous_secret_settings import (
    PreviousSecretSettings,
)
from app.schemas.typings.platform.strings import PlatformSecret
from app.utilities.config_helpers.app_settings.environment_variable_readers import (
    optional_text,
)


class PreviousSecretSettingsSection(TypedDict):
    """The `AppSettings` field of the secrets in rotation."""

    previous_secrets: PreviousSecretSettings


def read_previous_secret_settings(
    environment_variables: Mapping[str, str],
) -> PreviousSecretSettingsSection:
    """All optional; a blank value is no previous value."""

    def previous(variable_name: str) -> PlatformSecret | None:
        return optional_text(environment_variables, variable_name, PlatformSecret)

    return PreviousSecretSettingsSection(
        previous_secrets=PreviousSecretSettings(
            elevenlabs_webhook_secret=previous("ELEVENLABS_WEBHOOK_SECRET_PREVIOUS"),
            meta_app_secret=previous("META_APP_SECRET_PREVIOUS"),
            flitt_secret_key=previous("FLITT_SECRET_KEY_PREVIOUS"),
            zadarma_api_secret=previous("ZADARMA_API_SECRET_PREVIOUS"),
            twilio_auth_token=previous("TWILIO_AUTH_TOKEN_PREVIOUS"),
        )
    )
