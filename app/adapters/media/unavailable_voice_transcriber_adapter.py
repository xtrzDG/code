from app.contracts.channel_media import VoiceTranscriberContract
from app.schemas.dto.media import VoiceTranscriptionInput, VoiceTranscriptionResult
from app.schemas.exceptions.media_errors import TranscriptionNotConfiguredError


class UnavailableVoiceTranscriberAdapter(VoiceTranscriberContract):
    """
    No speech-to-text (LLM_PROVIDER=scripted: offline runs, staging without
    keys): every voice note is answered with the request to write.
    """

    def transcribe(self, request: VoiceTranscriptionInput) -> VoiceTranscriptionResult:
        del request
        raise TranscriptionNotConfiguredError(
            "Voice notes are not transcribed with the offline language model."
        )
