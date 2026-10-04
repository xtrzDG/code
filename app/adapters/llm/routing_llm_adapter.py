from collections.abc import Sequence

from app.adapters.llm.llm_payloads import (
    build_tool_results_payload,
    build_user_media_payload,
    build_user_text_payload,
)
from app.contracts.llm import LlmAdapterContract
from app.schemas.constants.assistants import LlmProvider
from app.schemas.dto.conversations import LlmRequest, LlmResponse, LlmToolResult
from app.schemas.dto.media import LlmImageInput
from app.schemas.exceptions.application_errors import ExternalServiceError
from app.schemas.typings.conversations.strings import LlmProviderPayload, MessageText
from app.utilities.conversations.llm_models import resolve_llm_provider


class RoutingLlmAdapter(LlmAdapterContract):
    """
    Provider-neutral entry point: each request goes to the adapter of the
    provider that serves its model id ("gpt-*"/"o<digit>*" OpenAI,
    "claude-*" Anthropic, "scripted" the offline model).

    Conversations are pinned to an assistant version and a version to one
    model id, so a replayed transcript always reaches the provider that
    produced its assistant turns. User turns are canonical for every
    provider.
    """

    def __init__(
        self,
        openai_adapter: LlmAdapterContract,
        anthropic_adapter: LlmAdapterContract,
        scripted_adapter: LlmAdapterContract | None = None,
    ) -> None:
        self._adapters: dict[LlmProvider, LlmAdapterContract] = {
            LlmProvider.OPENAI: openai_adapter,
            LlmProvider.ANTHROPIC: anthropic_adapter,
        }
        if scripted_adapter is not None:
            self._adapters[LlmProvider.SCRIPTED] = scripted_adapter

    def build_user_text_turn(self, text: MessageText) -> LlmProviderPayload:
        return build_user_text_payload(text)

    def build_user_media_turn(
        self,
        text: MessageText,
        images: Sequence[LlmImageInput],
    ) -> LlmProviderPayload:
        return build_user_media_payload(text, images)

    def build_tool_results_turn(
        self,
        results: list[LlmToolResult],
    ) -> LlmProviderPayload:
        return build_tool_results_payload(results)

    def complete(self, request: LlmRequest) -> LlmResponse:
        provider: LlmProvider | None = resolve_llm_provider(request.model_id)
        adapter: LlmAdapterContract | None = (
            None if provider is None else self._adapters.get(provider)
        )
        if adapter is None:
            raise ExternalServiceError(
                f"No language-model provider is configured for model "
                f"{request.model_id}."
            )

        return adapter.complete(request)
