"""Thin typed seams over the language-model provider SDKs.

Arguments are plain JSON-shaped values at the SDK boundary; the adapters own
the conversion from and to the provider-neutral DTOs. Implementations raise
ExternalServiceError for every SDK, transport or configuration failure.
"""

from typing import Protocol

from anthropic.types.beta import BetaMessage
from openai.types.audio import Transcription
from openai.types.responses import Response

from app.contracts.client_contract import ClientContract


class OpenAiResponsesClientContract(ClientContract, Protocol):
    def create_response(
        self,
        *,
        model: str,
        instructions: str,
        input_items: list[dict[str, object]],
        tools: list[dict[str, object]],
        reasoning_effort: str | None,
        max_output_tokens: int,
        text_format: dict[str, object] | None = None,
        timeout_seconds: float | None = None,
        max_retries: int | None = None,
    ) -> Response:
        """
        One stateless Responses API call (`store=False`, encrypted reasoning
        returned so it can be replayed). `timeout_seconds` and `max_retries`
        bound this call instead of the client's defaults.
        """
        raise NotImplementedError


class AnthropicMessagesClientContract(ClientContract, Protocol):
    def create_message(
        self,
        *,
        model: str,
        max_tokens: int,
        system: list[dict[str, object]],
        tools: list[dict[str, object]],
        messages: list[dict[str, object]],
        effort: str | None,
        is_fallback_enabled: bool,
        timeout_seconds: float | None = None,
        max_retries: int | None = None,
    ) -> BetaMessage:
        """
        One Messages API call; `effort` None leaves `output_config` out, and
        server-side refusal fallbacks are asked for only when enabled (models
        that do not support an option reject the whole request).
        `timeout_seconds` and `max_retries` bound this call instead of the
        client's defaults.
        """
        raise NotImplementedError


class OpenAiTranscriptionClientContract(ClientContract, Protocol):
    def transcribe(
        self,
        *,
        model: str,
        audio: bytes,
        file_name: str,
        language: str | None,
        languages: list[str],
        keywords: list[str],
    ) -> Transcription:
        """
        One speech-to-text call (`/audio/transcriptions`, JSON). `language`
        pins the language; `languages` and `keywords` hint the models that
        take them (empty: not sent). Raises TranscriptionNotConfiguredError
        without an API key, ExternalServiceError for every other failure.
        """
        raise NotImplementedError
