from app.contracts.channel_clients import ElevenLabsApiClientContract
from app.contracts.recording_storage import RecordingStorageAdapterContract
from app.schemas.typings.conversations.strings import (
    ProviderCallId,
    RecordingStoragePath,
)
from app.utilities.channels.voice_recordings import read_voice_platform_call_id


class ElevenLabsRecordingStorageAdapter(RecordingStorageAdapterContract):
    """
    Call recordings kept by ElevenLabs (concept section 7: voice data stays
    in the voice platform's EU storage).

    Paths "elevenlabs/conversations/<conversation id>" are deleted on the
    platform (audio and transcript); any other path goes to `fallback`
    storage (local files, object storage) when one is given.
    """

    def __init__(
        self,
        elevenlabs_client: ElevenLabsApiClientContract,
        fallback: RecordingStorageAdapterContract | None = None,
    ) -> None:
        self._elevenlabs_client: ElevenLabsApiClientContract = elevenlabs_client
        self._fallback: RecordingStorageAdapterContract | None = fallback

    def delete(self, recording_path: RecordingStoragePath) -> None:
        conversation_id: ProviderCallId | None = read_voice_platform_call_id(
            recording_path
        )
        if conversation_id is not None:
            self._elevenlabs_client.delete_conversation(conversation_id)
        elif self._fallback is not None:
            self._fallback.delete(recording_path)
