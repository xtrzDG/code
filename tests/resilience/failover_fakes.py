"""Language models that fail, answer slowly or refuse, for failover tests."""

import json
import time
from collections.abc import Callable

from typed_time_provider import MonotonicClock, Nanoseconds

from app.adapters.llm.routing_llm_adapter import RoutingLlmAdapter
from app.adapters.llm.scripted_llm_adapter import ScriptedLlmAdapter
from app.facilitators.resilience.circuit_breaker_facilitator import (
    CircuitBreakerFacilitator,
)
from app.schemas.constants.assistants import LlmEffort
from app.schemas.dto.conversations import LlmRequest, LlmResponse
from app.schemas.dto.llm_scripts import ScriptedLlmTurn
from app.schemas.exceptions.application_errors import (
    ExternalServiceError,
    LlmRefusedError,
)
from app.schemas.typings.assistants.constrained_integers import LlmMaxOutputTokens
from app.schemas.typings.assistants.constrained_strings import LlmModelId
from app.schemas.typings.assistants.strings import SystemPromptText
from app.schemas.typings.conversations.strings import LlmProviderPayload, MessageText

PRIMARY_MODEL: LlmModelId = LlmModelId("gpt-5-mini")
FALLBACK_MODEL: LlmModelId = LlmModelId("claude-sonnet-5-5")


def answering(text: str) -> ScriptedLlmAdapter:
    return ScriptedLlmAdapter(lambda request: ScriptedLlmTurn(text=MessageText(text)))


def failing(seconds: float = 0.0) -> ScriptedLlmAdapter:
    """A provider that is down (after `seconds`, as a timeout would be)."""

    def fail(request: LlmRequest) -> ScriptedLlmTurn:
        del request
        time.sleep(seconds)
        raise ExternalServiceError("OpenAI response failed: server_error.")

    return ScriptedLlmAdapter(fail)


def refusing() -> ScriptedLlmAdapter:
    def refuse(request: LlmRequest) -> ScriptedLlmTurn:
        del request
        raise LlmRefusedError("The OpenAI model declined to answer.")

    return ScriptedLlmAdapter(refuse)


def real_breaker() -> CircuitBreakerFacilitator:
    return CircuitBreakerFacilitator(
        MonotonicClock(preferred_time_unit_type=Nanoseconds)
    )


def router(
    openai: ScriptedLlmAdapter,
    anthropic: ScriptedLlmAdapter,
    breaker: CircuitBreakerFacilitator | None = None,
    fallback_model_id: LlmModelId | None = FALLBACK_MODEL,
) -> RoutingLlmAdapter:
    return RoutingLlmAdapter(
        openai_adapter=openai,
        anthropic_adapter=anthropic,
        circuit_breaker=real_breaker() if breaker is None else breaker,
        fallback_model_id=fallback_model_id,
    )


def build_request(
    model_id: LlmModelId = PRIMARY_MODEL,
    transcript: list[str] | None = None,
    fallback_transcript: list[str] | None = None,
) -> LlmRequest:
    return LlmRequest(
        model_id=model_id,
        system_prompt=SystemPromptText("system"),
        tools=[],
        transcript=[LlmProviderPayload(turn) for turn in transcript or []],
        max_output_tokens=LlmMaxOutputTokens(100),
        effort=LlmEffort.LOW,
        fallback_transcript=(
            None
            if fallback_transcript is None
            else [LlmProviderPayload(turn) for turn in fallback_transcript]
        ),
    )


def timed[Result](call: Callable[[], Result]) -> tuple[Result, float]:
    started: float = time.monotonic()
    result: Result = call()
    return result, time.monotonic() - started


class OpenAiShapedAdapter(ScriptedLlmAdapter):
    """
    The version's provider: answers in the OpenAI transcript format (with
    reasoning another provider cannot replay) until it is switched off.
    """

    def __init__(self, text: str) -> None:
        super().__init__(lambda request: ScriptedLlmTurn(text=MessageText(text)))
        self.is_down: bool = False

    def complete(self, request: LlmRequest) -> LlmResponse:
        if self.is_down:
            self.requests.append(request)
            raise ExternalServiceError("OpenAI response failed: server_error.")

        response: LlmResponse = super().complete(request)
        return response.model_copy(
            update={
                "assistant_turn_payload": LlmProviderPayload(
                    json.dumps(
                        {
                            "role": "assistant",
                            "provider": "openai",
                            "items": [
                                {"type": "reasoning", "encrypted_content": "gAAA"},
                                {
                                    "type": "message",
                                    "role": "assistant",
                                    "content": [
                                        {
                                            "type": "output_text",
                                            "text": str(response.text),
                                        }
                                    ],
                                },
                            ],
                        }
                    )
                )
            }
        )
