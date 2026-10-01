import logging

import pytest

from app.adapters.llm.routing_llm_adapter import RoutingLlmAdapter
from app.adapters.llm.scripted_llm_adapter import ScriptedLlmAdapter
from app.schemas.constants.assistants import LlmEffort, LlmProvider
from app.schemas.dto.conversations import LlmRequest
from app.schemas.dto.llm_scripts import ScriptedLlmTurn
from app.schemas.exceptions.application_errors import ExternalServiceError
from app.schemas.typings.assistants.constrained_integers import LlmMaxOutputTokens
from app.schemas.typings.assistants.constrained_strings import LlmModelId
from app.schemas.typings.assistants.strings import SystemPromptText
from app.schemas.typings.conversations.constrained_integers import LlmTokenCount
from app.schemas.typings.conversations.strings import MessageText
from app.utilities.conversations.llm_models import (
    compute_llm_call_cost,
    resolve_llm_provider,
)


def scripted(text: str) -> ScriptedLlmAdapter:
    return ScriptedLlmAdapter(lambda request: ScriptedLlmTurn(text=MessageText(text)))


def build_request(model_id: str) -> LlmRequest:
    return LlmRequest(
        model_id=LlmModelId(model_id),
        system_prompt=SystemPromptText("system"),
        tools=[],
        transcript=[],
        max_output_tokens=LlmMaxOutputTokens(100),
        effort=LlmEffort.LOW,
    )


@pytest.mark.parametrize(
    ("model_id", "provider"),
    [
        ("gpt-5-mini", LlmProvider.OPENAI),
        ("gpt-5-mini-2025-08-07", LlmProvider.OPENAI),
        ("o4-mini", LlmProvider.OPENAI),
        ("claude-opus-5-5", LlmProvider.ANTHROPIC),
        ("claude-sonnet-5-5", LlmProvider.ANTHROPIC),
        ("scripted", LlmProvider.SCRIPTED),
        ("gemini-3-pro", None),
        ("orca-7b", None),
    ],
)
def test_provider_is_resolved_from_the_model_id(
    model_id: str,
    provider: LlmProvider | None,
) -> None:
    assert resolve_llm_provider(LlmModelId(model_id)) == provider


def test_routing_keeps_each_conversation_on_its_provider() -> None:
    openai_adapter = scripted("from openai")
    anthropic_adapter = scripted("from anthropic")
    scripted_adapter = scripted("from script")
    router = RoutingLlmAdapter(openai_adapter, anthropic_adapter, scripted_adapter)

    answers = [
        router.complete(build_request(model_id)).text
        for model_id in ("gpt-5-mini", "claude-opus-5-5", "scripted", "o4-mini")
    ]

    assert answers == ["from openai", "from anthropic", "from script", "from openai"]
    assert router.build_user_text_turn(MessageText("Hi")) == (
        openai_adapter.build_user_text_turn(MessageText("Hi"))
    )


def test_routing_rejects_models_without_a_configured_provider() -> None:
    router = RoutingLlmAdapter(scripted("a"), scripted("b"))

    for model_id in ("scripted", "mistral-large"):
        with pytest.raises(ExternalServiceError, match="No language-model provider"):
            router.complete(build_request(model_id))


def test_costs_follow_the_price_table() -> None:
    mini = compute_llm_call_cost(
        LlmModelId("gpt-5-mini"), LlmTokenCount(10_000), LlmTokenCount(1_000)
    )
    snapshot = compute_llm_call_cost(
        LlmModelId("gpt-5-mini-2025-08-07"), LlmTokenCount(3), LlmTokenCount(1)
    )
    opus = compute_llm_call_cost(
        LlmModelId("claude-opus-5-5"), LlmTokenCount(1_000), LlmTokenCount(500)
    )

    assert (mini.input_cost, mini.output_cost, mini.total) == (2_500, 2_000, 4_500)
    assert (snapshot.input_cost, snapshot.output_cost) == (1, 2)
    assert (opus.input_cost, opus.output_cost) == (4_000, 10_000)


def test_unknown_models_cost_nothing_and_warn(caplog: pytest.LogCaptureFixture) -> None:
    with caplog.at_level(logging.WARNING):
        cost = compute_llm_call_cost(
            LlmModelId("future-model-9"), LlmTokenCount(5_000), LlmTokenCount(500)
        )

    assert cost.total == 0
    assert "future-model-9" in caplog.text
