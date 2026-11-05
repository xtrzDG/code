from app.contracts.channel_clients import ElevenLabsApiClientContract
from app.contracts.recording_storage import RecordingStorageAdapterContract
from app.schemas.dto.call_recordings import (
    RecordingAudio,
    RecordingByteRange,
    RecordingLocation,
    RecordingPart,
)
from app.schemas.exceptions.application_errors import ValidationFailedError
from app.schemas.typings.conversations.strings import ProviderCallId
from app.utilities.channels.voice_recordings import read_voice_platform_call_id
from app.utilities.recordings.recording_byte_ranges import cut_recording_part


class ElevenLabsRecordingStorageAdapter(RecordingStorageAdapterContract):
    """
    Call recordings kept by ElevenLabs (in its EU storage) until they are
    archived into the platform's own storage.

    Paths "elevenlabs/conversations/<conversation id>" are played back from
    the platform (the conversation audio, downloadable only whole) and
    deleted there (audio and transcript); any other path goes to `fallback`
    storage (EU object storage, local files in development) when one is
    given.
    """

    def __init__(
        self,
        elevenlabs_client: ElevenLabsApiClientContract,
        fallback: RecordingStorageAdapterContract | None = None,
    ) -> None:
        self._elevenlabs_client: ElevenLabsApiClientContract = elevenlabs_client
        self._fallback: RecordingStorageAdapterContract | None = fallback

    def read(
        self,
        location: RecordingLocation,
        wanted: RecordingByteRange | None = None,
    ) -> RecordingPart | None:
        conversation_id: ProviderCallId | None = read_voice_platform_call_id(
            location.path
        )
        if conversation_id is not None:
            audio: RecordingAudio | None = (
                self._elevenlabs_client.get_conversation_audio(conversation_id)
            )
            return None if audio is None else cut_recording_part(audio, wanted)

        if self._fallback is None:
            return None

        return self._fallback.read(location, wanted)

    def store(self, location: RecordingLocation, audio: RecordingAudio) -> None:
        if (
            read_voice_platform_call_id(location.path) is not None
            or self._fallback is None
        ):
            raise ValidationFailedError(
                f"Recordings cannot be stored at {location.path!r}: the voice "
                "platform keeps its own."
            )

        self._fallback.store(location, audio)

    def delete(self, location: RecordingLocation) -> None:
        conversation_id: ProviderCallId | None = read_voice_platform_call_id(
            location.path
        )
        if conversation_id is not None:
            self._elevenlabs_client.delete_conversation(conversation_id)
        elif self._fallback is not None:
            self._fallback.delete(location)
