import threading
from collections.abc import Sequence

from app.contracts.llm import LlmAdapterContract
from app.schemas.dto.conversations import (
    LlmRequest,
    LlmResponse,
    LlmToolResult,
)
from app.schemas.dto.media import LlmImageInput
from app.schemas.exceptions.application_errors import ExternalServiceError
from app.schemas.typings.assistants.constrained_integers import (
    LlmCallTimeoutSeconds,
    LlmConcurrencyLimit,
)
from app.schemas.typings.conversations.strings import LlmProviderPayload, MessageText


class ConcurrencyLimitedLlmAdapter(LlmAdapterContract):
    """
    At most LLM_MAX_CONCURRENCY model calls of this process at once.

    A model call holds a request thread for seconds; without a bound, a
    burst of customer messages (or a slow provider) would hold every thread
    of the process (THREADPOOL_SIZE) and the cabinet would stop answering.
    A call beyond the bound waits for a free place for as long as one call
    may take (LLM_CALL_TIMEOUT_SECONDS), then fails like a provider error
    (the customer's reply goes to a colleague). The wait is not part of the
    traced call: the limit wraps the traced adapter.
    """

    def __init__(
        self,
        inner_adapter: LlmAdapterContract,
        max_concurrency: LlmConcurrencyLimit,
        wait_seconds: LlmCallTimeoutSeconds,
    ) -> None:
        self._inner_adapter: LlmAdapterContract = inner_adapter
        self._places: threading.BoundedSemaphore = threading.BoundedSemaphore(
            int(max_concurrency)
        )
        self._max_concurrency: LlmConcurrencyLimit = max_concurrency
        self._wait_seconds: LlmCallTimeoutSeconds = wait_seconds

    def build_user_text_turn(self, text: MessageText) -> LlmProviderPayload:
        return self._inner_adapter.build_user_text_turn(text)

    def build_user_media_turn(
        self,
        text: MessageText,
        images: Sequence[LlmImageInput],
    ) -> LlmProviderPayload:
        return self._inner_adapter.build_user_media_turn(text, images)

    def build_tool_results_turn(
        self,
        results: list[LlmToolResult],
    ) -> LlmProviderPayload:
        return self._inner_adapter.build_tool_results_turn(results)

    def complete(self, request: LlmRequest) -> LlmResponse:
        if not self._places.acquire(timeout=float(int(self._wait_seconds))):
            raise ExternalServiceError(
                f"All {int(self._max_concurrency)} model call places of this "
                f"process stayed busy for {int(self._wait_seconds)} s "
                "(LLM_MAX_CONCURRENCY)."
            )

        try:
            return self._inner_adapter.complete(request)
        finally:
            self._places.release()
