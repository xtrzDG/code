from collections.abc import Sequence

from app.contracts.llm import LlmAdapterContract
from app.schemas.dto.conversations import (
    LlmCallLimits,
    LlmRequest,
    LlmResponse,
    LlmToolResult,
)
from app.schemas.dto.media import LlmImageInput
from app.schemas.typings.assistants.constrained_integers import LlmCallRetryLimit
from app.schemas.typings.conversations.strings import LlmProviderPayload, MessageText

# One retry: a provider hiccup is retried once, a provider outage is not
# waited out while the customer waits.
CHAT_CALL_RETRY_LIMIT: LlmCallRetryLimit = LlmCallRetryLimit(1)


class CallLimitedLlmAdapter(LlmAdapterContract):
    """
    The language model of a customer chat: every call is bounded by
    LLM_CALL_TIMEOUT_SECONDS and retried at most `retry_limit` times, so a
    slow provider costs a waiting customer about a minute, not three (the
    reply then goes to a colleague). Background work (autotest customers
    and judges, menu imports) keeps the client's longer defaults.
    """

    def __init__(
        self, inner_adapter: LlmAdapterContract, limits: LlmCallLimits
    ) -> None:
        self._inner_adapter: LlmAdapterContract = inner_adapter
        self._limits: LlmCallLimits = limits

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
        return self._inner_adapter.complete(
            request.model_copy(update={"call_limits": self._limits})
        )
