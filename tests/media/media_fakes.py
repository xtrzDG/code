"""Fakes of the customer-media seams: storage, platform downloads, speech-to-text."""

import struct

from app.contracts.channel_media import (
    ChannelMediaFetcherContract,
    VoiceTranscriberContract,
)
from app.contracts.media_storage import MediaStorageAdapterContract
from app.schemas.dto.media import (
    ChannelMediaRequest,
    FetchedMedia,
    MediaLocation,
    StoredMediaFile,
    VoiceTranscriptionInput,
    VoiceTranscriptionResult,
)
from app.schemas.exceptions.media_errors import MediaUnavailableError
from app.schemas.typings.media.constrained_integers import AudioDurationSeconds
from app.schemas.typings.media.strings import ProviderMediaType, TranscribedVoiceText

OPUS_SAMPLES_PER_SECOND: int = 48_000


def ogg_opus_bytes(seconds: int = 7) -> bytes:
    """A tiny Ogg Opus stream: the head page and a last page `seconds` long."""

    head: bytes = b"OggS" + bytes(24) + b"OpusHead" + bytes(11)
    last: bytes = (
        b"OggS"
        + b"\x00\x04"
        + struct.pack("<q", seconds * OPUS_SAMPLES_PER_SECOND)
        + bytes(16)
    )
    return head + bytes(64) + last


def jpeg_bytes() -> bytes:
    return b"\xff\xd8\xff\xe0\x00\x10JFIF\x00" + bytes(200) + b"\xff\xd9"


def png_bytes() -> bytes:
    return b"\x89PNG\r\n\x1a\n" + bytes(64)


class InMemoryMediaStorage(MediaStorageAdapterContract):
    """Files by business and path; `is_failing` makes every call fail."""

    def __init__(self) -> None:
        self.files: dict[tuple[str, str], StoredMediaFile] = {}

    def store(self, location: MediaLocation, media: StoredMediaFile) -> None:
        self.files[(str(location.business_id), str(location.path))] = media

    def read(self, location: MediaLocation) -> StoredMediaFile | None:
        return self.files.get((str(location.business_id), str(location.path)))

    def delete(self, location: MediaLocation) -> None:
        self.files.pop((str(location.business_id), str(location.path)), None)


class FakeMediaFetcher(ChannelMediaFetcherContract):
    """
    Serves `files` by provider media id; an id mapped to an exception raises
    it (one failure per call while `failures` last). Requests are recorded.
    """

    def __init__(self) -> None:
        self.files: dict[str, bytes] = {}
        self.failures: dict[str, list[Exception]] = {}
        self.requests: list[ChannelMediaRequest] = []

    def fetch(self, request: ChannelMediaRequest) -> FetchedMedia:
        self.requests.append(request)
        pending: list[Exception] = self.failures.get(str(request.provider_media_id), [])
        if pending:
            raise pending.pop(0)

        content: bytes | None = self.files.get(str(request.provider_media_id))
        if content is None:
            raise MediaUnavailableError("No such file.")

        return FetchedMedia(
            content=content, declared_type=ProviderMediaType("application/octet-stream")
        )


class FakeVoiceTranscriber(VoiceTranscriberContract):
    """Answers `texts` in order (the last one again); `failures` first."""

    def __init__(self, texts: list[str] | None = None) -> None:
        self.texts: list[str] = texts or ["I would like a table for four at seven."]
        self.failures: list[Exception] = []
        self.billed_seconds: int | None = None
        self.requests: list[VoiceTranscriptionInput] = []

    def transcribe(self, request: VoiceTranscriptionInput) -> VoiceTranscriptionResult:
        self.requests.append(request)
        if self.failures:
            raise self.failures.pop(0)

        text: str = self.texts.pop(0) if len(self.texts) > 1 else self.texts[0]
        return VoiceTranscriptionResult(
            text=TranscribedVoiceText(text),
            billed_seconds=(
                None
                if self.billed_seconds is None
                else AudioDurationSeconds(self.billed_seconds)
            ),
        )
