import threading
from collections.abc import Callable

import openai
from openai.types import CreateEmbeddingResponse

from app.contracts.embedding_clients import OpenAiEmbeddingsClientContract
from app.schemas.exceptions.application_errors import ExternalServiceError
from app.schemas.typings.channels.constrained_strings import PublicBaseUrl
from app.schemas.typings.platform.strings import PlatformIdentifier, PlatformSecret

type OpenAiSdkFactory = Callable[[], openai.OpenAI]

# Two budgets. A search waits for its query's embedding while a customer
# (or a caller, whose tool answer has 8 s in all) waits for the reply: one
# try of at most QUERY_TIMEOUT_SECONDS, then the search stays lexical. The
# `index_knowledge` job waits for nobody and may retry a slow endpoint.
QUERY_TIMEOUT_SECONDS: float = 1.2
QUERY_MAX_RETRIES: int = 0
INDEX_TIMEOUT_SECONDS: float = 20.0
INDEX_MAX_RETRIES: int = 2


class OpenAiEmbeddingsClient(OpenAiEmbeddingsClientContract):
    """
    The OpenAI Embeddings API at the configured base URL (the EU
    data-residency endpoint by default) with its own key
    (EMBEDDINGS_API_KEY) in the configured project. The SDK client is
    created on first use, with this client's time budget (the query or the
    indexing one above).
    """

    def __init__(
        self,
        api_key: PlatformSecret | None,
        base_url: PublicBaseUrl,
        project_id: PlatformIdentifier | None,
        sdk_factory: OpenAiSdkFactory | None = None,
        timeout_seconds: float = INDEX_TIMEOUT_SECONDS,
        max_retries: int = INDEX_MAX_RETRIES,
    ) -> None:
        self._timeout_seconds: float = timeout_seconds
        self._max_retries: int = max_retries
        self._api_key: PlatformSecret | None = api_key
        self._base_url: PublicBaseUrl = base_url
        self._project_id: PlatformIdentifier | None = project_id
        self._sdk_factory: OpenAiSdkFactory = (
            sdk_factory if sdk_factory is not None else self._build_sdk_client
        )
        self._lock: threading.Lock = threading.Lock()
        self._sdk_client: openai.OpenAI | None = None

    def create_embeddings(self, *, model: str, texts: list[str]) -> list[list[float]]:
        sdk_client: openai.OpenAI = self._get_sdk_client()
        try:
            response: CreateEmbeddingResponse = sdk_client.embeddings.create(
                model=model, input=texts, encoding_format="float"
            )
        except openai.APIStatusError as error:
            raise ExternalServiceError(
                f"OpenAI embeddings returned HTTP {error.status_code}."
            ) from error
        except openai.APITimeoutError as error:
            raise ExternalServiceError(
                "OpenAI embeddings did not answer in time."
            ) from error
        except openai.OpenAIError as error:
            raise ExternalServiceError(
                f"OpenAI embeddings failed: {type(error).__name__}."
            ) from error

        by_index: dict[int, list[float]] = {
            entry.index: list(entry.embedding) for entry in response.data
        }
        if sorted(by_index) != list(range(len(texts))):
            raise ExternalServiceError(
                f"OpenAI embeddings answered {len(by_index)} vectors "
                f"for {len(texts)} texts."
            )

        return [by_index[index] for index in range(len(texts))]

    def _get_sdk_client(self) -> openai.OpenAI:
        with self._lock:
            if self._sdk_client is None:
                try:
                    self._sdk_client = self._sdk_factory()
                except openai.OpenAIError as error:
                    raise ExternalServiceError(
                        "Knowledge embeddings are off: set EMBEDDINGS_API_KEY."
                    ) from error

            return self._sdk_client

    def _build_sdk_client(self) -> openai.OpenAI:
        if self._api_key is None:
            raise ExternalServiceError(
                "Knowledge embeddings are off: set EMBEDDINGS_API_KEY."
            )

        return openai.OpenAI(
            api_key=str(self._api_key),
            base_url=str(self._base_url),
            project=None if self._project_id is None else str(self._project_id),
            timeout=self._timeout_seconds,
            max_retries=self._max_retries,
        )
