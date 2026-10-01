"""Recording paths of calls whose audio stays with the voice platform."""

from pathlib import PurePosixPath

from app.schemas.typings.conversations.constrained_strings import RecordingMediaType
from app.schemas.typings.conversations.strings import (
    ProviderCallId,
    RecordingStoragePath,
)

# The audio and transcript of an ElevenLabs call stay in its (EU) storage;
# the path names the conversation so retention can delete it there.
ELEVENLABS_RECORDING_PREFIX: str = "elevenlabs/conversations/"
# ElevenLabs serves conversation audio as MP3.
DEFAULT_RECORDING_MEDIA_TYPE: RecordingMediaType = RecordingMediaType("audio/mpeg")
# Audio files a recordings directory may hold, by extension.
RECORDING_MEDIA_TYPES_BY_EXTENSION: dict[str, RecordingMediaType] = {
    ".mp3": RecordingMediaType("audio/mpeg"),
    ".mpeg": RecordingMediaType("audio/mpeg"),
    ".wav": RecordingMediaType("audio/wav"),
    ".ogg": RecordingMediaType("audio/ogg"),
    ".oga": RecordingMediaType("audio/ogg"),
    ".opus": RecordingMediaType("audio/ogg"),
    ".m4a": RecordingMediaType("audio/mp4"),
    ".aac": RecordingMediaType("audio/aac"),
    ".webm": RecordingMediaType("audio/webm"),
    ".flac": RecordingMediaType("audio/flac"),
}


def build_voice_platform_recording_path(
    provider_call_id: ProviderCallId,
) -> RecordingStoragePath:
    return RecordingStoragePath(f"{ELEVENLABS_RECORDING_PREFIX}{provider_call_id}")


def read_voice_platform_call_id(
    recording_path: RecordingStoragePath,
) -> ProviderCallId | None:
    """The conversation of a voice-platform recording path; None for others."""

    path_text: str = str(recording_path)
    if not path_text.startswith(ELEVENLABS_RECORDING_PREFIX):
        return None

    conversation_id: str = path_text.removeprefix(ELEVENLABS_RECORDING_PREFIX)
    if conversation_id == "" or "/" in conversation_id:
        return None

    return ProviderCallId(conversation_id)


def read_recording_media_type(content_type: str | None) -> RecordingMediaType:
    """
    The audio type a platform declared ("audio/mpeg; charset=…" ->
    "audio/mpeg"); MP3 when it declared none or something that is not audio
    (a generic "application/octet-stream").
    """

    declared: str = (content_type or "").split(";", 1)[0].strip().lower()
    try:
        return RecordingMediaType(declared)
    except ValueError:
        return DEFAULT_RECORDING_MEDIA_TYPE


def recording_media_type_of_file(file_name: str) -> RecordingMediaType:
    """The audio type of a recording file by its extension; MP3 when unknown."""

    extension: str = PurePosixPath(file_name).suffix.lower()
    return RECORDING_MEDIA_TYPES_BY_EXTENSION.get(
        extension, DEFAULT_RECORDING_MEDIA_TYPE
    )
