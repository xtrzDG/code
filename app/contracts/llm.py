"""Provider-neutral language-model contract."""

from typing import Protocol

from app.contracts.adapter_contract import AdapterContract
from app.schemas.dto.conversations import LlmRequest, LlmResponse, LlmToolResult
from app.schemas.typings.conversations.strings import LlmProviderPayload, MessageText


class LlmAdapterContract(AdapterContract, Protocol):
    """
    Talks to a language model and owns the provider transcript format.

    The conversation engine never parses payloads: it asks the adapter to build
    user turns, stores every payload verbatim, and replays them unchanged.
    """

    def build_user_text_turn(self, text: MessageText) -> LlmProviderPayload:
        raise NotImplementedError

    def build_tool_results_turn(
        self,
        results: list[LlmToolResult],
    ) -> LlmProviderPayload:
        raise NotImplementedError

    def complete(self, request: LlmRequest) -> LlmResponse:
        """
        Run one model request.

        Raises:
            ExternalServiceError: provider unavailable or misconfigured.
            LlmRefusedError: the model and its fallbacks declined.
        """
        raise NotImplementedError
