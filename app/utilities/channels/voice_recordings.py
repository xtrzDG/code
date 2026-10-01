"""Recording paths of calls whose audio stays with the voice platform."""

from app.schemas.typings.conversations.strings import (
    ProviderCallId,
    RecordingStoragePath,
)

# The audio and transcript of an ElevenLabs call stay in its (EU) storage;
# the path names the conversation so retention can delete it there.
ELEVENLABS_RECORDING_PREFIX: str = "elevenlabs/conversations/"


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
