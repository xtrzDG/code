"""Helpers for conversation engine tests: a token-counting model and request readers."""

import json
from typing import Any

from app.adapters.llm.scripted_llm_adapter import ScriptedLlmAdapter
from app.contracts.llm import LlmAdapterContract
from app.schemas.dto.conversations import LlmRequest, LlmResponse, LlmToolResult
from app.schemas.typings.conversations.constrained_integers import LlmTokenCount
from app.schemas.typings.conversations.strings import LlmProviderPayload, MessageText
from tests.brain.brain_world import BrainWorld


class CountingLlmAdapter(LlmAdapterContract):
    """Scripted model that reports token usage like a real provider."""

    def __init__(
        self,
        inner: ScriptedLlmAdapter,
        input_tokens: int,
        output_tokens: int,
    ) -> None:
        self.inner: ScriptedLlmAdapter = inner
        self._input_tokens: int = input_tokens
        self._output_tokens: int = output_tokens

    def build_user_text_turn(self, text: MessageText) -> LlmProviderPayload:
        return self.inner.build_user_text_turn(text)

    def build_tool_results_turn(
        self,
        results: list[LlmToolResult],
    ) -> LlmProviderPayload:
        return self.inner.build_tool_results_turn(results)

    def complete(self, request: LlmRequest) -> LlmResponse:
        response: LlmResponse = self.inner.complete(request)
        return response.model_copy(
            update={
                "input_tokens": LlmTokenCount(self._input_tokens),
                "output_tokens": LlmTokenCount(self._output_tokens),
            }
        )


def user_turn_text(payload: LlmProviderPayload) -> str:
    content: list[dict[str, Any]] = json.loads(payload)["content"]
    return "".join(block.get("text", "") for block in content)


def requests_of(world: BrainWorld) -> list[LlmRequest]:
    assert isinstance(world.llm, ScriptedLlmAdapter)
    return world.llm.requests
