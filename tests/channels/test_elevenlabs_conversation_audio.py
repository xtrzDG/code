"""Call recordings read back from the voice platform (ElevenLabs)."""

import httpx
import pytest

from app.adapters.voice.elevenlabs_recording_storage_adapter import (
    ElevenLabsRecordingStorageAdapter,
)
from app.clients.elevenlabs.elevenlabs_client import ElevenLabsClient
from app.clients.elevenlabs.unconfigured_elevenlabs_client import (
    UnconfiguredElevenLabsClient,
)
from app.contracts.recording_storage import RecordingStorageAdapterContract
from app.schemas.dto.call_recordings import (
    RecordingAudio,
    RecordingByteRange,
    RecordingLocation,
    RecordingPart,
)
from app.schemas.exceptions.application_errors import ExternalServiceError
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.channels.constrained_strings import PublicBaseUrl
from app.schemas.typings.conversations.constrained_strings import RecordingMediaType
from app.schemas.typings.conversations.strings import (
    ProviderCallId,
    RecordingStoragePath,
)
from app.schemas.typings.platform.strings import PlatformSecret
from app.utilities.recordings.recording_byte_ranges import cut_recording_part

EU_BASE_URL: PublicBaseUrl = PublicBaseUrl("https://api.eu.residency.elevenlabs.io")
MP3: bytes = b"ID3\x04\x00\x00frames"


class AudioPlatform:
    """MockTransport answering every request with one scripted response."""

    def __init__(self, response: httpx.Response | Exception) -> None:
        self.response: httpx.Response | Exception = response
        self.requests: list[httpx.Request] = []

    def client(self) -> ElevenLabsClient:
        return ElevenLabsClient(
            api_key=PlatformSecret("xi-key"),
            base_url=EU_BASE_URL,
            transport=httpx.MockTransport(self._handle),
        )

    def _handle(self, request: httpx.Request) -> httpx.Response:
        self.requests.append(request)
        if isinstance(self.response, Exception):
            raise self.response

        return self.response


def test_conversation_audio_is_read_from_the_eu_platform() -> None:
    platform = AudioPlatform(
        httpx.Response(200, content=MP3, headers={"content-type": "audio/mpeg"})
    )

    audio = platform.client().get_conversation_audio(ProviderCallId("conv_7"))

    assert audio is not None
    assert (audio.content, str(audio.media_type)) == (MP3, "audio/mpeg")
    [request] = platform.requests
    assert request.method == "GET"
    assert str(request.url) == (
        "https://api.eu.residency.elevenlabs.io/v1/convai/conversations/conv_7/audio"
    )
    assert request.headers["xi-api-key"] == "xi-key"


@pytest.mark.parametrize(
    ("content_type", "media_type"),
    [
        ("audio/mpeg; charset=binary", "audio/mpeg"),
        ("Audio/WAV", "audio/wav"),
        ("application/octet-stream", "audio/mpeg"),
        (None, "audio/mpeg"),
    ],
)
def test_the_declared_audio_type_is_kept_and_anything_else_is_mp3(
    content_type: str | None,
    media_type: str,
) -> None:
    headers: dict[str, str] = (
        {} if content_type is None else {"content-type": content_type}
    )
    platform = AudioPlatform(httpx.Response(200, content=MP3, headers=headers))

    audio = platform.client().get_conversation_audio(ProviderCallId("conv_7"))

    assert audio is not None
    assert str(audio.media_type) == media_type


def test_conversation_ids_stay_one_path_segment() -> None:
    platform = AudioPlatform(httpx.Response(404, json={"detail": "not found"}))

    platform.client().get_conversation_audio(ProviderCallId("conv/../agents/x"))

    [request] = platform.requests
    assert request.url.raw_path == (
        b"/v1/convai/conversations/conv%2F..%2Fagents%2Fx/audio"
    )


@pytest.mark.parametrize(
    "response",
    [
        httpx.Response(404, json={"detail": {"message": "Conversation not found"}}),
        httpx.Response(200, content=b"", headers={"content-type": "audio/mpeg"}),
    ],
)
def test_missing_audio_is_no_recording(response: httpx.Response) -> None:
    platform = AudioPlatform(response)

    assert platform.client().get_conversation_audio(ProviderCallId("conv_7")) is None


@pytest.mark.parametrize(
    "response",
    [
        httpx.Response(401, json={"detail": {"message": "Invalid API key"}}),
        httpx.Response(500, text="upstream failure"),
        httpx.ConnectError("refused"),
    ],
)
def test_platform_failures_are_external_service_errors(
    response: httpx.Response | Exception,
) -> None:
    platform = AudioPlatform(response)

    with pytest.raises(ExternalServiceError) as raised:
        platform.client().get_conversation_audio(ProviderCallId("conv_7"))

    assert "xi-key" not in str(raised.value)


def test_unconfigured_platform_reports_the_missing_key() -> None:
    with pytest.raises(ExternalServiceError):
        UnconfiguredElevenLabsClient().get_conversation_audio(ProviderCallId("c"))


class FallbackStorage(RecordingStorageAdapterContract):
    def __init__(self) -> None:
        self.reads: list[str] = []

    def read(
        self,
        location: RecordingLocation,
        wanted: RecordingByteRange | None = None,
    ) -> RecordingPart | None:
        self.reads.append(str(location.path))
        audio = RecordingAudio(
            content=b"OggS", media_type=RecordingMediaType("audio/ogg")
        )
        return cut_recording_part(audio, wanted)

    def store(self, location: RecordingLocation, audio: RecordingAudio) -> None:
        raise AssertionError("Playback stores nothing.")

    def delete(self, location: RecordingLocation) -> None:
        raise AssertionError("Playback deletes nothing.")


def at(path: str) -> RecordingLocation:
    return RecordingLocation(business_id=BusinessId(), path=RecordingStoragePath(path))


def test_platform_paths_play_from_the_platform_and_others_from_the_fallback() -> None:
    platform = AudioPlatform(
        httpx.Response(200, content=MP3, headers={"content-type": "audio/mpeg"})
    )
    fallback = FallbackStorage()
    storage = ElevenLabsRecordingStorageAdapter(platform.client(), fallback)

    from_platform = storage.read(at("elevenlabs/conversations/conv_7"))
    from_fallback = storage.read(at("calls/2026/call.ogg"))
    without_fallback = ElevenLabsRecordingStorageAdapter(platform.client()).read(
        at("calls/2026/call.ogg")
    )

    assert from_platform is not None and from_platform.content == MP3
    assert (int(from_platform.first_byte), int(from_platform.total_bytes)) == (
        0,
        len(MP3),
    )
    assert from_fallback is not None and from_fallback.content == b"OggS"
    assert without_fallback is None
    assert [request.url.path for request in platform.requests] == [
        "/v1/convai/conversations/conv_7/audio"
    ]
    assert fallback.reads == ["calls/2026/call.ogg"]
