"""
Model calls for /metrics: time, outcome and tokens by provider and the
model that answered (a fallback when one stood in); a refusal is the
model's answer, not an error, and a model of no known provider is left
out.
"""

from collections.abc import Sequence

import pytest
from prometheus_client import CollectorRegistry
from typed_time_provider import MonotonicClock, Nanoseconds

from app.adapters.llm.metered_llm_adapter import MeteredLlmAdapter
from app.adapters.llm.offline_llm_adapter import OfflineLlmAdapter
from app.schemas.constants.assistants import LlmEffort
from app.schemas.dto.conversations import LlmRequest, LlmResponse
from app.schemas.exceptions.application_errors import (
    ExternalServiceError,
    LlmRefusedError,
)
from app.schemas.typings.assistants.constrained_integers import LlmMaxOutputTokens
from app.schemas.typings.assistants.constrained_strings import LlmModelId
from app.schemas.typings.assistants.strings import SystemPromptText
from app.schemas.typings.conversations.constrained_integers import LlmTokenCount
from app.schemas.typings.conversations.strings import MessageText
from app.utilities.observability.metrics.prometheus_service_metrics import (
    PrometheusServiceMetrics,
)
from app.utilities.observability.tracing.span_tracer import NO_SPAN_TRACER

SECOND: int = 1_000_000_000
CLAUDE: str = "claude-sonnet-5-5"
GPT: str = "gpt-5.5-mini"


class Ticks:
    def __init__(self) -> None:
        self.now: int = 1_000 * SECOND

    def clock(self) -> MonotonicClock[Nanoseconds]:
        return MonotonicClock(
            preferred_time_unit_type=Nanoseconds,
            monotonic_nanosecond_factory=lambda: self.now,
        )


class ScriptedModel(OfflineLlmAdapter):
    """Answers or fails in turn; each call takes two seconds of the ticks."""

    def __init__(
        self, ticks: Ticks, outcomes: Sequence[Exception | LlmResponse]
    ) -> None:
        super().__init__()
        self._ticks: Ticks = ticks
        self._outcomes: list[Exception | LlmResponse] = list(outcomes)

    def complete(self, request: LlmRequest) -> LlmResponse:
        self._ticks.now += 2 * SECOND
        outcome = self._outcomes.pop(0)
        if isinstance(outcome, Exception):
            raise outcome
        return outcome


def model_request(model_id: str) -> LlmRequest:
    return LlmRequest(
        model_id=LlmModelId(model_id),
        system_prompt=SystemPromptText("You are the assistant of a bakery."),
        tools=[],
        transcript=[OfflineLlmAdapter().build_user_text_turn(MessageText("Hi"))],
        max_output_tokens=LlmMaxOutputTokens(100),
        effort=LlmEffort.LOW,
    )


def answer(fallback: str | None = None) -> LlmResponse:
    base = OfflineLlmAdapter().complete(model_request("scripted"))
    return base.model_copy(
        update={
            "input_tokens": LlmTokenCount(120),
            "output_tokens": LlmTokenCount(30),
            "fallback_model_id": None if fallback is None else LlmModelId(fallback),
        }
    )


def test_calls_are_measured_by_the_model_that_answered() -> None:
    ticks, registry = Ticks(), CollectorRegistry()
    model = MeteredLlmAdapter(
        ScriptedModel(
            ticks,
            [
                answer(),
                answer(fallback=GPT),
                ExternalServiceError("overloaded"),
                LlmRefusedError("no"),
            ],
        ),
        PrometheusServiceMetrics(registry),
        NO_SPAN_TRACER,
        ticks.clock(),
    )

    model.complete(model_request(CLAUDE))
    model.complete(model_request(CLAUDE))
    for error_type in (ExternalServiceError, LlmRefusedError):
        with pytest.raises(error_type):
            model.complete(model_request(CLAUDE))

    def calls(provider: str, model_id: str, outcome: str) -> float | None:
        return registry.get_sample_value(
            "workshop_llm_call_duration_seconds_count",
            {"provider": provider, "model": model_id, "outcome": outcome},
        )

    assert calls("anthropic", CLAUDE, "ok") == 1
    assert calls("openai", GPT, "ok") == 1
    assert calls("anthropic", CLAUDE, "error") == 1
    assert calls("anthropic", CLAUDE, "refused") == 1
    assert (
        registry.get_sample_value(
            "workshop_llm_call_duration_seconds_sum",
            {"provider": "anthropic", "model": CLAUDE, "outcome": "ok"},
        )
        == 2.0
    )
    assert (
        registry.get_sample_value(
            "workshop_llm_tokens_total",
            {"provider": "anthropic", "model": CLAUDE, "direction": "input"},
        )
        == 120
    )
    assert (
        registry.get_sample_value(
            "workshop_llm_tokens_total",
            {"provider": "openai", "model": GPT, "direction": "output"},
        )
        == 30
    )


def test_a_model_of_no_known_provider_is_not_measured() -> None:
    ticks, registry = Ticks(), CollectorRegistry()
    model = MeteredLlmAdapter(
        ScriptedModel(ticks, [answer()]),
        PrometheusServiceMetrics(registry),
        NO_SPAN_TRACER,
        ticks.clock(),
    )

    model.complete(model_request("mistral-large"))

    assert "workshop_llm_call_duration_seconds_count" not in str(
        [sample.name for metric in registry.collect() for sample in metric.samples]
    )
