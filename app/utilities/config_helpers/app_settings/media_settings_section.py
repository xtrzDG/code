"""LLM_TRANSCRIBE_MODEL and MEDIA_MAX_*: voice notes and photos of customers."""

from collections.abc import Mapping
from typing import TypedDict

from app.schemas.configurations.media_settings import (
    DEFAULT_MAX_IMAGE_BYTES,
    DEFAULT_MAX_VOICE_BYTES,
    DEFAULT_MAX_VOICE_SECONDS,
    DEFAULT_TRANSCRIPTION_MODEL_ID,
    MediaSettings,
)
from app.schemas.typings.media.constrained_integers import (
    MediaByteLimit,
    VoiceDurationLimitSeconds,
)
from app.schemas.typings.media.constrained_strings import TranscriptionModelId
from app.utilities.config_helpers.app_settings.environment_variable_readers import (
    parse_setting,
    read_integer,
    read_text,
)


class MediaSettingsSection(TypedDict):
    """The `AppSettings` field of customer media."""

    media: MediaSettings


def read_media_settings(
    environment_variables: Mapping[str, str],
) -> MediaSettingsSection:
    """Defaults fit WhatsApp's voice notes and every model's photo limit."""

    return MediaSettingsSection(
        media=MediaSettings(
            transcription_model_id=parse_setting(
                "LLM_TRANSCRIBE_MODEL",
                read_text(
                    environment_variables,
                    "LLM_TRANSCRIBE_MODEL",
                    DEFAULT_TRANSCRIPTION_MODEL_ID,
                ),
                TranscriptionModelId,
            ),
            max_voice_bytes=parse_setting(
                "MEDIA_MAX_VOICE_BYTES",
                read_integer(
                    environment_variables,
                    "MEDIA_MAX_VOICE_BYTES",
                    DEFAULT_MAX_VOICE_BYTES,
                ),
                MediaByteLimit,
            ),
            max_image_bytes=parse_setting(
                "MEDIA_MAX_IMAGE_BYTES",
                read_integer(
                    environment_variables,
                    "MEDIA_MAX_IMAGE_BYTES",
                    DEFAULT_MAX_IMAGE_BYTES,
                ),
                MediaByteLimit,
            ),
            max_voice_seconds=parse_setting(
                "MEDIA_MAX_VOICE_SECONDS",
                read_integer(
                    environment_variables,
                    "MEDIA_MAX_VOICE_SECONDS",
                    DEFAULT_MAX_VOICE_SECONDS,
                ),
                VoiceDurationLimitSeconds,
            ),
        )
    )
