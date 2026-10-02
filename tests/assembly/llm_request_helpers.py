"""A token-reporting model wrapper and readers of a model request's transcript."""

import json
from typing import cast

from app.contracts.llm import LlmAdapterContract
from app.schemas.dto.conversations import (
    LlmRequest,
    LlmResponse,
    LlmToolResult,
)
from app.schemas.typings.conversations.constrained_integers import LlmTokenCount
from app.schemas.typings.conversations.strings import LlmProviderPayload, MessageText


class TokenReportingLlmAdapter(LlmAdapterContract):
    """Wraps an adapter and reports fixed token counts on every response."""

    def __init__(
        self,
        inner_adapter: LlmAdapterContract,
        input_tokens: int,
        output_tokens: int,
    ) -> None:
        self._inner_adapter: LlmAdapterContract = inner_adapter
        self._input_tokens: LlmTokenCount = LlmTokenCount(input_tokens)
        self._output_tokens: LlmTokenCount = LlmTokenCount(output_tokens)

    def build_user_text_turn(self, text: MessageText) -> LlmProviderPayload:
        return self._inner_adapter.build_user_text_turn(text)

    def build_tool_results_turn(
        self,
        results: list[LlmToolResult],
    ) -> LlmProviderPayload:
        return self._inner_adapter.build_tool_results_turn(results)

    def complete(self, request: LlmRequest) -> LlmResponse:
        response: LlmResponse = self._inner_adapter.complete(request)
        return response.model_copy(
            update={
                "input_tokens": self._input_tokens,
                "output_tokens": self._output_tokens,
            }
        )


def read_last_user_text(request: LlmRequest) -> str:
    """Text of the last user turn of a request (canonical payload format)."""

    payload = cast(dict[str, object], json.loads(request.transcript[-1]))
    content = cast(list[dict[str, object]], payload["content"])
    return str(content[0]["text"])


def count_assistant_turns(request: LlmRequest) -> int:
    """How many model turns the transcript already holds."""

    return sum(
        1
        for payload in request.transcript
        if cast(dict[str, object], json.loads(payload))["role"] == "assistant"
    )
