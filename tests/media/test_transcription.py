"""
Speech-to-text of voice notes: the OpenAI client (EU base URL, the real SDK
over a mock transport), language hints and keywords per model, billed
seconds, errors, and the offline fallback.
"""

from collections.abc import Callable

import httpx2
import openai
import pytest

from app.adapters.media.openai_voice_transcriber_adapter import (
    OpenAiVoiceTranscriberAdapter,
    unique_base_languages,
)
from app.adapters.media.unavailable_voice_transcriber_adapter import (
    UnavailableVoiceTranscriberAdapter,
)
from app.adapters.media.voice_transcriber_factory import build_voice_transcriber
from app.clients.openai.openai_transcription_client import OpenAiTranscriptionClient
from app.schemas.dto.media import StoredMediaFile, VoiceTranscriptionInput
from app.schemas.exceptions.application_errors import ExternalServiceError
from app.schemas.exceptions.media_errors import TranscriptionNotConfiguredError
from app.schemas.typings.businesses.strings import BusinessName
from app.schemas.typings.channels.constrained_strings import PublicBaseUrl
from app.schemas.typings.localization.constrained_strings import LanguageTag
from app.schemas.typings.media.constrained_strings import (
    MessageMediaType,
    TranscriptionModelId,
)
from tests.channels.channels_settings import build_settings
from tests.media.media_fakes import ogg_opus_bytes

EU_BASE_URL: str = "https://eu.api.openai.com/v1"

type Handler = Callable[[httpx2.Request], httpx2.Response]


def client_answering(
    handler: Handler,
) -> tuple[OpenAiTranscriptionClient, list[httpx2.Request]]:
    seen: list[httpx2.Request] = []

    def answer(request: httpx2.Request) -> httpx2.Response:
        seen.append(request)
        return handler(request)

    def sdk() -> openai.OpenAI:
        return openai.OpenAI(
            api_key="test-key-0000",
            base_url=EU_BASE_URL,
            max_retries=0,
            http_client=httpx2.Client(transport=httpx2.MockTransport(answer)),
        )

    return (
        OpenAiTranscriptionClient(
            base_url=PublicBaseUrl(EU_BASE_URL), project_id=None, sdk_factory=sdk
        ),
        seen,
    )


def transcribed(text: str, seconds: float | None = 7.2) -> Handler:
    body: dict[str, object] = {"text": text}
    if seconds is not None:
        body["usage"] = {"type": "duration", "seconds": seconds}
    return lambda request: httpx2.Response(200, json=body)


def voice_input(
    model: str, languages: list[str], keywords: list[str] | None = None
) -> VoiceTranscriptionInput:
    return VoiceTranscriptionInput(
        audio=StoredMediaFile(
            content=ogg_opus_bytes(), media_type=MessageMediaType("audio/ogg")
        ),
        model_id=TranscriptionModelId(model),
        language_hints=[LanguageTag(tag) for tag in languages],
        keywords=[BusinessName(word) for word in keywords or []],
    )


def form_fields(request: httpx2.Request) -> str:
    return request.content.decode("utf-8", errors="replace")


class TestOpenAiTranscriber:
    def test_one_language_is_passed_to_a_single_language_model(self) -> None:
        client, seen = client_answering(transcribed(" Есть столик на четверых? "))
        adapter = OpenAiVoiceTranscriberAdapter(client)

        result = adapter.transcribe(
            voice_input("gpt-4o-transcribe", ["ru-RU"], ["Mtsvane Ezo"])
        )

        assert result.text == "Есть столик на четверых?"
        assert result.billed_seconds == 8
        [request] = seen
        assert str(request.url) == f"{EU_BASE_URL}/audio/transcriptions"
        fields = form_fields(request)
        assert 'name="model"\r\n\r\ngpt-4o-transcribe' in fields
        assert 'name="language"\r\n\r\nru' in fields
        assert 'filename="voice.ogg"' in fields
        # Keywords and lists only go to models that take them.
        assert 'name="keywords' not in fields
        assert 'name="languages' not in fields

    def test_several_languages_let_the_model_recognize_the_language(self) -> None:
        client, seen = client_answering(transcribed("გამარჯობა"))
        OpenAiVoiceTranscriberAdapter(client).transcribe(
            voice_input("gpt-4o-mini-transcribe", ["ka", "ru", "en"])
        )

        assert 'name="language"' not in form_fields(seen[0])

    def test_a_model_that_takes_lists_gets_every_language_and_the_name(self) -> None:
        client, seen = client_answering(transcribed("Hello"))
        OpenAiVoiceTranscriberAdapter(client).transcribe(
            voice_input("gpt-transcribe", ["ka-GE", "ru", "ka", "en"], ["Mtsvane Ezo"])
        )

        fields = form_fields(seen[0])
        assert fields.count('name="languages[]"') == 3
        assert 'name="keywords[]"\r\n\r\nMtsvane Ezo' in fields
        assert 'name="language"\r\n' not in fields

    def test_no_usage_means_no_billed_seconds_and_silence_is_empty_text(self) -> None:
        client, _ = client_answering(transcribed("   ", seconds=None))
        result = OpenAiVoiceTranscriberAdapter(client).transcribe(
            voice_input("gpt-4o-transcribe", [])
        )

        assert result.text == ""
        assert result.billed_seconds is None

    @pytest.mark.parametrize("status", [400, 429, 500, 503])
    def test_service_errors_are_external_failures(self, status: int) -> None:
        client, _ = client_answering(
            lambda request: httpx2.Response(status, json={"error": {"message": "no"}})
        )
        with pytest.raises(ExternalServiceError, match=f"HTTP {status}"):
            OpenAiVoiceTranscriberAdapter(client).transcribe(
                voice_input("gpt-4o-transcribe", ["en"])
            )

    def test_timeouts_and_connection_errors_are_external_failures(self) -> None:
        def timeout(request: httpx2.Request) -> httpx2.Response:
            raise httpx2.ReadTimeout("slow", request=request)

        client, _ = client_answering(timeout)
        with pytest.raises(ExternalServiceError, match="in time"):
            OpenAiVoiceTranscriberAdapter(client).transcribe(
                voice_input("gpt-4o-transcribe", ["en"])
            )

        def refused(request: httpx2.Request) -> httpx2.Response:
            raise httpx2.ConnectError("refused", request=request)

        client, _ = client_answering(refused)
        with pytest.raises(ExternalServiceError, match="APIConnectionError"):
            OpenAiVoiceTranscriberAdapter(client).transcribe(
                voice_input("gpt-4o-transcribe", ["en"])
            )

    def test_a_missing_key_means_transcription_is_not_configured(self) -> None:
        def no_key() -> openai.OpenAI:
            raise openai.OpenAIError("The api_key client option must be set")

        client = OpenAiTranscriptionClient(
            base_url=PublicBaseUrl(EU_BASE_URL), project_id=None, sdk_factory=no_key
        )
        with pytest.raises(TranscriptionNotConfiguredError, match="OPENAI_API_KEY"):
            OpenAiVoiceTranscriberAdapter(client).transcribe(
                voice_input("gpt-4o-transcribe", ["en"])
            )

    def test_the_sdk_client_is_built_once(self) -> None:
        built: list[int] = []

        def sdk() -> openai.OpenAI:
            built.append(1)
            return openai.OpenAI(
                api_key="test-key-0000",
                base_url=EU_BASE_URL,
                max_retries=0,
                http_client=httpx2.Client(
                    transport=httpx2.MockTransport(transcribed("ok"))
                ),
            )

        client = OpenAiTranscriptionClient(
            base_url=PublicBaseUrl(EU_BASE_URL), project_id=None, sdk_factory=sdk
        )
        adapter = OpenAiVoiceTranscriberAdapter(client)
        adapter.transcribe(voice_input("gpt-4o-transcribe", ["en"]))
        adapter.transcribe(voice_input("gpt-4o-transcribe", ["en"]))
        assert built == [1]


def test_language_hints_become_unique_base_codes() -> None:
    assert unique_base_languages(["ka-GE", "ka", "RU", "en-US", "fil", "x"]) == [
        "ka",
        "ru",
        "en",
    ]


def test_the_offline_model_has_no_speech_to_text() -> None:
    with pytest.raises(TranscriptionNotConfiguredError):
        UnavailableVoiceTranscriberAdapter().transcribe(
            voice_input("gpt-4o-transcribe", ["en"])
        )


def test_the_factory_picks_by_language_model_provider() -> None:
    client, _ = client_answering(transcribed("ok"))

    scripted = build_voice_transcriber(build_settings(LLM_PROVIDER="scripted"), client)
    openai_backed = build_voice_transcriber(
        build_settings(LLM_PROVIDER="openai"), client
    )
    anthropic = build_voice_transcriber(
        build_settings(LLM_PROVIDER="anthropic", ANTHROPIC_API_KEY="test-key-0000"),
        client,
    )

    assert isinstance(scripted, UnavailableVoiceTranscriberAdapter)
    assert isinstance(openai_backed, OpenAiVoiceTranscriberAdapter)
    # Anthropic has no speech-to-text: OpenAI's EU project transcribes.
    assert isinstance(anthropic, OpenAiVoiceTranscriberAdapter)


def test_the_answer_is_asked_for_as_json() -> None:
    client, seen = client_answering(transcribed("ok"))
    OpenAiVoiceTranscriberAdapter(client).transcribe(
        voice_input("gpt-4o-transcribe", ["en"])
    )
    assert 'name="response_format"\r\n\r\njson' in form_fields(seen[0])
