"""Seams of customer files: fetching them from a platform, transcribing voice."""

from typing import Protocol

from app.contracts.adapter_contract import AdapterContract
from app.schemas.dto.media import (
    ChannelMediaRequest,
    FetchedMedia,
    VoiceTranscriptionInput,
    VoiceTranscriptionResult,
)


class ChannelMediaFetcherContract(AdapterContract, Protocol):
    """Downloads a file a customer sent from the messaging platform."""

    def fetch(self, request: ChannelMediaRequest) -> FetchedMedia:
        """
        The file, never larger than `request.max_bytes`.

        Raises:
            MediaTooLargeError: the file is over the cap (declared or read).
            MediaUnavailableError: the platform no longer has the file, or
                the request names one it does not hand out.
            ExternalServiceError: a temporary failure (asking later helps).
        """
        raise NotImplementedError


class VoiceTranscriberContract(AdapterContract, Protocol):
    """Turns a voice note into text (speech-to-text in the EU)."""

    def transcribe(self, request: VoiceTranscriptionInput) -> VoiceTranscriptionResult:
        """
        What was said (empty text: no speech). Raises ExternalServiceError
        when the service is not configured, refuses or fails.
        """
        raise NotImplementedError
