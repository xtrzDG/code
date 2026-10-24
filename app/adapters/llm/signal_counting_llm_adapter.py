from collections.abc import Sequence

from app.contracts.llm import LlmAdapterContract
from app.contracts.monitoring import SignalCounterAdapterContract
from app.schemas.constants.monitoring import PlatformSignal
from app.schemas.dto.conversations import LlmRequest, LlmResponse, LlmToolResult
from app.schemas.dto.media import LlmImageInput
from app.schemas.exceptions.application_errors import (
    ExternalServiceError,
    LlmRefusedError,
)
from app.schemas.typings.conversations.strings import LlmProviderPayload, MessageText


class SignalCountingLlmAdapter(LlmAdapterContract):
    """
    Decorator that counts every model call, and every call the provider
    failed (an outage, a timeout, a rate limit: not a refusal, which is the
    model's answer), in the shared platform signals: the LLM error-rate
    alert reads them. Otherwise it behaves like the wrapped adapter.
    """

    def __init__(
        self,
        inner_adapter: LlmAdapterContract,
        signal_counter: SignalCounterAdapterContract,
    ) -> None:
        self._inner_adapter: LlmAdapterContract = inner_adapter
        self._signal_counter: SignalCounterAdapterContract = signal_counter

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
        self._signal_counter.count(PlatformSignal.LLM_CALL)
        try:
            return self._inner_adapter.complete(request)
        except LlmRefusedError:
            raise
        except ExternalServiceError:
            self._signal_counter.count(PlatformSignal.LLM_ERROR)
            raise
