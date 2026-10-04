import logging
from collections.abc import Sequence

from app.adapters.llm.llm_payloads import (
    build_tool_results_payload,
    build_user_media_payload,
    build_user_text_payload,
)
from app.contracts.llm import LlmAdapterContract
from app.contracts.resilience import CircuitBreakerContract
from app.schemas.constants.assistants import LlmProvider
from app.schemas.dto.conversations import LlmRequest, LlmResponse, LlmToolResult
from app.schemas.dto.media import LlmImageInput
from app.schemas.exceptions.application_errors import (
    ExternalServiceError,
    LlmRefusedError,
)
from app.schemas.typings.assistants.constrained_strings import LlmModelId
from app.schemas.typings.conversations.strings import LlmProviderPayload, MessageText
from app.schemas.typings.resilience.constrained_strings import CircuitName
from app.utilities.conversations.llm_models import resolve_llm_provider

logger: logging.Logger = logging.getLogger(__name__)


class RoutingLlmAdapter(LlmAdapterContract):
    """
    Provider-neutral entry point: each request goes to the adapter of the
    provider that serves its model id ("gpt-*"/"o<digit>*" OpenAI,
    "claude-*" Anthropic, "scripted" the offline model).

    Failover: every provider and model has a circuit breaker. When the
    requested model's provider fails (after its own timeout and retries)
    or its circuit is open, the request is rerun on `fallback_model_id`
    with the request's provider-neutral transcript (`fallback_transcript`:
    the other provider cannot replay this one's reasoning); an open circuit
    is skipped at once instead of waited on. A refusal is the model's
    answer, not an outage: it is never rerun elsewhere. Without a fallback
    model (or for the fallback model itself) errors are raised as they are.

    User turns are canonical for every provider; an assistant turn of
    another provider in a replayed transcript is converted by the adapter
    that receives it.
    """

    def __init__(
        self,
        openai_adapter: LlmAdapterContract,
        anthropic_adapter: LlmAdapterContract,
        scripted_adapter: LlmAdapterContract | None = None,
        circuit_breaker: CircuitBreakerContract | None = None,
        fallback_model_id: LlmModelId | None = None,
    ) -> None:
        self._adapters: dict[LlmProvider, LlmAdapterContract] = {
            LlmProvider.OPENAI: openai_adapter,
            LlmProvider.ANTHROPIC: anthropic_adapter,
        }
        if scripted_adapter is not None:
            self._adapters[LlmProvider.SCRIPTED] = scripted_adapter

        self._circuit_breaker: CircuitBreakerContract | None = circuit_breaker
        self._fallback_model_id: LlmModelId | None = fallback_model_id

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
        fallback_model_id: LlmModelId | None = self._fallback_for(request.model_id)
        if fallback_model_id is None:
            return self._call(request)

        if not self._allows_call(request.model_id):
            logger.info(
                "The circuit of %s is open: %s answers instead.",
                request.model_id,
                fallback_model_id,
            )
            return self._call_fallback(request, fallback_model_id, None)

        try:
            return self._call(request)
        except LlmRefusedError:
            raise
        except ExternalServiceError as error:
            logger.warning(
                "%s failed (%s): rerunning the call on %s.",
                request.model_id,
                error,
                fallback_model_id,
            )
            return self._call_fallback(request, fallback_model_id, error)

    def _call(self, request: LlmRequest) -> LlmResponse:
        """One call of the request's model, reported to its circuit."""

        adapter: LlmAdapterContract = self._adapter_for(request.model_id)
        try:
            response: LlmResponse = adapter.complete(request)
        except LlmRefusedError:
            self._report(request.model_id, is_success=True)
            raise
        except ExternalServiceError:
            self._report(request.model_id, is_success=False)
            raise

        self._report(request.model_id, is_success=True)
        return response

    def _call_fallback(
        self,
        request: LlmRequest,
        fallback_model_id: LlmModelId,
        cause: ExternalServiceError | None,
    ) -> LlmResponse:
        """
        The request on the fallback model; the original failure is raised
        when the fallback cannot answer either (or its circuit is open too).
        """

        if not self._allows_call(fallback_model_id):
            raise cause or ExternalServiceError(
                f"{request.model_id} and its fallback {fallback_model_id} are "
                "both unavailable."
            )

        transcript: list[LlmProviderPayload] = (
            request.transcript
            if request.fallback_transcript is None
            else request.fallback_transcript
        )
        try:
            response: LlmResponse = self._call(
                request.model_copy(
                    update={
                        "model_id": fallback_model_id,
                        "transcript": list(transcript),
                        "fallback_transcript": None,
                    }
                )
            )
        except LlmRefusedError:
            raise
        except ExternalServiceError as error:
            raise (cause or error) from error

        return response.model_copy(update={"fallback_model_id": fallback_model_id})

    def _allows_call(self, model_id: LlmModelId) -> bool:
        return self._circuit_breaker is None or self._circuit_breaker.allows_call(
            circuit_name(model_id)
        )

    def _report(self, model_id: LlmModelId, *, is_success: bool) -> None:
        if self._circuit_breaker is None:
            return

        if is_success:
            self._circuit_breaker.record_success(circuit_name(model_id))
        else:
            self._circuit_breaker.record_failure(circuit_name(model_id))

    def _fallback_for(self, model_id: LlmModelId) -> LlmModelId | None:
        """The fallback model of a request, when there is a usable one."""

        fallback: LlmModelId | None = self._fallback_model_id
        if fallback is None or fallback == model_id:
            return None

        provider: LlmProvider | None = resolve_llm_provider(fallback)
        if provider is None or provider not in self._adapters:
            return None

        return fallback

    def _adapter_for(self, model_id: LlmModelId) -> LlmAdapterContract:
        provider: LlmProvider | None = resolve_llm_provider(model_id)
        adapter: LlmAdapterContract | None = (
            None if provider is None else self._adapters.get(provider)
        )
        if adapter is None:
            raise ExternalServiceError(
                f"No language-model provider is configured for model {model_id}."
            )

        return adapter


def circuit_name(model_id: LlmModelId) -> CircuitName:
    """The circuit of a model: its provider and the model id."""

    provider: LlmProvider | None = resolve_llm_provider(model_id)
    provider_name: str = "unknown" if provider is None else provider.value
    return CircuitName(f"{provider_name}:{model_id}")
