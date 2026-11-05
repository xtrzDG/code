"""Provider-neutral language-model contract."""

from collections.abc import Sequence
from typing import Protocol

from app.contracts.adapter_contract import AdapterContract
from app.schemas.dto.conversations import LlmRequest, LlmResponse, LlmToolResult
from app.schemas.dto.media import LlmImageInput
from app.schemas.typings.conversations.strings import LlmProviderPayload, MessageText


class LlmAdapterContract(AdapterContract, Protocol):
    """
    Talks to a language model and owns the provider transcript format.

    The conversation engine never parses payloads: it asks the adapter to build
    user turns, stores every payload verbatim, and replays them unchanged.
    """

    def build_user_text_turn(self, text: MessageText) -> LlmProviderPayload:
        raise NotImplementedError

    def build_user_media_turn(
        self,
        text: MessageText,
        images: Sequence[LlmImageInput],
    ) -> LlmProviderPayload:
        """
        A user turn with the photos a customer sent next to the text. The
        turn keeps references to the stored photos (the transcript stays
        small, and a purged photo is gone from it too); they are read when
        a request is made. An adapter that shows no pictures sends the text.
        """
        del images
        return self.build_user_text_turn(text)

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
