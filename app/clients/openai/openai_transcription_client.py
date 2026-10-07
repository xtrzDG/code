import threading
from collections.abc import Callable

import openai
from openai.types.audio import Transcription

from app.contracts.llm_clients import OpenAiTranscriptionClientContract
from app.schemas.exceptions.application_errors import ExternalServiceError
from app.schemas.exceptions.media_errors import TranscriptionNotConfiguredError
from app.schemas.typings.channels.constrained_strings import PublicBaseUrl
from app.schemas.typings.platform.strings import PlatformIdentifier

type OpenAiSdkFactory = Callable[[], openai.OpenAI]

# A voice note of a few minutes is transcribed in seconds; the cap keeps a
# stuck call from holding the worker.
REQUEST_TIMEOUT_SECONDS: float = 60.0
MAX_RETRIES: int = 2


class OpenAiTranscriptionClient(OpenAiTranscriptionClientContract):
    """
    Speech-to-text of the OpenAI Audio API at the configured base URL (the
    EU data-residency endpoint by default) in the configured project, the
    same as the language model. The SDK client is created on first use, so
    the application starts without OPENAI_API_KEY; voice notes then get a
    request to write instead.
    """

    def __init__(
        self,
        base_url: PublicBaseUrl,
        project_id: PlatformIdentifier | None,
        sdk_factory: OpenAiSdkFactory | None = None,
    ) -> None:
        self._base_url: PublicBaseUrl = base_url
        self._project_id: PlatformIdentifier | None = project_id
        self._sdk_factory: OpenAiSdkFactory = (
            sdk_factory if sdk_factory is not None else self._build_sdk_client
        )
        self._lock: threading.Lock = threading.Lock()
        self._sdk_client: openai.OpenAI | None = None

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
        sdk_client: openai.OpenAI = self._get_sdk_client()
        try:
            return sdk_client.audio.transcriptions.create(
                model=model,
                file=(file_name, audio),
                response_format="json",
                language=openai.omit if language is None else language,
                languages=languages if languages else openai.omit,
                keywords=keywords if keywords else openai.omit,
            )
        except openai.APIStatusError as error:
            raise ExternalServiceError(
                f"OpenAI transcription returned HTTP {error.status_code}."
            ) from error
        except openai.APITimeoutError as error:
            raise ExternalServiceError(
                "OpenAI transcription did not answer in time."
            ) from error
        except openai.OpenAIError as error:
            raise ExternalServiceError(
                f"OpenAI transcription failed: {type(error).__name__}."
            ) from error

    def _get_sdk_client(self) -> openai.OpenAI:
        with self._lock:
            if self._sdk_client is None:
                try:
                    self._sdk_client = self._sdk_factory()
                except openai.OpenAIError as error:
                    raise TranscriptionNotConfiguredError(
                        "Voice notes are not transcribed: set OPENAI_API_KEY."
                    ) from error

            return self._sdk_client

    def _build_sdk_client(self) -> openai.OpenAI:
        return openai.OpenAI(
            base_url=str(self._base_url),
            project=None if self._project_id is None else str(self._project_id),
            timeout=REQUEST_TIMEOUT_SECONDS,
            max_retries=MAX_RETRIES,
        )
