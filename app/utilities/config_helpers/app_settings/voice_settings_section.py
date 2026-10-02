"""ELEVENLABS_* and ZADARMA_*: voice agents and telephony, kept in the EU."""

from collections.abc import Mapping
from typing import TypedDict
from urllib.parse import urlsplit

from app.schemas.exceptions.application_errors import ValidationFailedError
from app.schemas.typings.channels.constrained_strings import PublicBaseUrl
from app.schemas.typings.platform.strings import PlatformSecret
from app.utilities.config_helpers.app_settings.environment_variable_readers import (
    optional_text,
    read_boolean,
    read_text,
)

# EU data residency of ElevenLabs: calls, transcripts and recordings stay in
# the EU (concept sections 7 and 10). Production refuses any other host
# unless ELEVENLABS_ALLOW_NON_EU_REGION is true.
DEFAULT_ELEVENLABS_API_BASE_URL: str = "https://api.eu.residency.elevenlabs.io"
ELEVENLABS_EU_HOST_SUFFIX: str = ".eu.residency.elevenlabs.io"
DEFAULT_ELEVENLABS_HOST: str = "api.eu.residency.elevenlabs.io"


class VoiceSettingsSection(TypedDict):
    """The `AppSettings` fields of the voice providers."""

    elevenlabs_api_key: PlatformSecret | None
    elevenlabs_webhook_secret: PlatformSecret | None
    elevenlabs_api_base_url: PublicBaseUrl
    zadarma_api_key: PlatformSecret | None
    zadarma_api_secret: PlatformSecret | None


def read_voice_settings(
    environment_variables: Mapping[str, str],
    is_production: bool,
) -> VoiceSettingsSection:
    def secret(variable_name: str) -> PlatformSecret | None:
        return optional_text(environment_variables, variable_name, PlatformSecret)

    return VoiceSettingsSection(
        elevenlabs_api_key=secret("ELEVENLABS_API_KEY"),
        elevenlabs_webhook_secret=secret("ELEVENLABS_WEBHOOK_SECRET"),
        elevenlabs_api_base_url=read_elevenlabs_base_url(
            environment_variables,
            is_production=is_production,
        ),
        zadarma_api_key=secret("ZADARMA_API_KEY"),
        zadarma_api_secret=secret("ZADARMA_API_SECRET"),
    )


def read_elevenlabs_base_url(
    environment_variables: Mapping[str, str],
    is_production: bool,
) -> PublicBaseUrl:
    """
    The ElevenLabs API host: the EU-residency one by default. In production
    another host is refused unless ELEVENLABS_ALLOW_NON_EU_REGION is true.

    Raises:
        ValidationFailedError: a non-EU host in production without the flag.
    """

    base_url = PublicBaseUrl(
        read_text(
            environment_variables,
            "ELEVENLABS_API_BASE_URL",
            DEFAULT_ELEVENLABS_API_BASE_URL,
        )
    )
    host: str = (urlsplit(str(base_url)).hostname or "").lower()
    is_eu_host: bool = host == DEFAULT_ELEVENLABS_HOST or host.endswith(
        ELEVENLABS_EU_HOST_SUFFIX
    )
    if (
        is_production
        and not is_eu_host
        and not read_boolean(
            environment_variables,
            "ELEVENLABS_ALLOW_NON_EU_REGION",
            False,
        )
    ):
        raise ValidationFailedError(
            f"ELEVENLABS_API_BASE_URL {base_url} keeps voice data outside the EU; "
            f"use {DEFAULT_ELEVENLABS_API_BASE_URL} or set "
            "ELEVENLABS_ALLOW_NON_EU_REGION=true."
        )

    return base_url
