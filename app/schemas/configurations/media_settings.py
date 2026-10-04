from base_pydantic_schemas import ImmutableDTO

from app.schemas.typings.media.constrained_integers import (
    MediaByteLimit,
    VoiceDurationLimitSeconds,
)
from app.schemas.typings.media.constrained_strings import TranscriptionModelId

DEFAULT_TRANSCRIPTION_MODEL_ID: str = "gpt-4o-transcribe"
DEFAULT_MAX_VOICE_BYTES: int = 16 * 1024 * 1024
DEFAULT_MAX_IMAGE_BYTES: int = 5 * 1024 * 1024
DEFAULT_MAX_VOICE_SECONDS: int = 300


class MediaSettings(ImmutableDTO):
    """
    Voice notes and photos customers send in the messengers: the
    speech-to-text model (LLM_TRANSCRIBE_MODEL, OpenAI's EU endpoint), the
    largest voice note and photo downloaded (MEDIA_MAX_VOICE_BYTES,
    MEDIA_MAX_IMAGE_BYTES; 5 MB is the largest photo every model reads) and
    the longest voice note transcribed (MEDIA_MAX_VOICE_SECONDS). Longer or
    larger ones get a polite request to write instead.
    """

    transcription_model_id: TranscriptionModelId = TranscriptionModelId(
        DEFAULT_TRANSCRIPTION_MODEL_ID
    )
    max_voice_bytes: MediaByteLimit = MediaByteLimit(DEFAULT_MAX_VOICE_BYTES)
    max_image_bytes: MediaByteLimit = MediaByteLimit(DEFAULT_MAX_IMAGE_BYTES)
    max_voice_seconds: VoiceDurationLimitSeconds = VoiceDurationLimitSeconds(
        DEFAULT_MAX_VOICE_SECONDS
    )
