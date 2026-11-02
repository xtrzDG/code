"""
The router calls only models it can reach: never the scripted model in
production, and a fallback model only when its provider's key is set (a
fallback without one is skipped, with one warning at startup, instead of
failing again at failover time).
"""

import logging

import pytest

from app.adapters.llm.routing_llm_adapter import RoutingLlmAdapter
from app.adapters.llm.routing_llm_adapter_factory import build_routing_llm_adapter
from app.adapters.llm.scripted_llm_adapter import ScriptedLlmAdapter
from app.schemas.configurations.app_settings import AppSettings
from app.schemas.exceptions.application_errors import ExternalServiceError
from app.schemas.typings.assistants.constrained_strings import LlmModelId
from app.utilities.config_helpers.app_settings.app_settings_assembler import (
    assemble_app_settings,
)
from app.utilities.config_helpers.llm_provider_keys import (
    missing_key_variable,
    report_unusable_fallback,
    usable_fallback_model_id,
)
from tests.platform.production_settings import production_with
from tests.resilience.failover_fakes import (
    FALLBACK_MODEL,
    answering,
    build_request,
    failing,
    real_breaker,
)

LOGGER_NAME: str = "app.utilities.config_helpers.llm_provider_keys"
OPENAI_ONLY: dict[str, str] = {"LLM_PROVIDER": "openai", "OPENAI_API_KEY": "fake"}


def test_the_settings_know_which_providers_have_a_key() -> None:
    both = assemble_app_settings({**OPENAI_ONLY, "ANTHROPIC_API_KEY": "fake"})
    blank = assemble_app_settings({"OPENAI_API_KEY": "  "})

    assert {provider.value for provider in both.keyed_llm_providers} == {
        "openai",
        "anthropic",
    }
    assert blank.keyed_llm_providers == frozenset()
    assert missing_key_variable(blank, LlmModelId("gpt-5-mini")) == "OPENAI_API_KEY"
    assert missing_key_variable(blank, LlmModelId("scripted")) is None
    assert missing_key_variable(both, LlmModelId("claude-sonnet-5-5")) is None


def test_a_fallback_without_its_key_is_skipped_with_one_warning(
    caplog: pytest.LogCaptureFixture,
) -> None:
    settings = assemble_app_settings(OPENAI_ONLY)

    with caplog.at_level(logging.WARNING, logger=LOGGER_NAME):
        skipped = report_unusable_fallback(settings)

    assert settings.reply_speed.llm_fallback_model_id == FALLBACK_MODEL
    assert usable_fallback_model_id(settings) is None
    assert skipped == FALLBACK_MODEL
    [warning] = caplog.records
    assert "LLM_FALLBACK_MODEL_ID claude-sonnet-5-5 is skipped" in warning.getMessage()
    assert "ANTHROPIC_API_KEY is not set" in warning.getMessage()


@pytest.mark.parametrize(
    "environment",
    [
        {**OPENAI_ONLY, "ANTHROPIC_API_KEY": "fake"},
        {**OPENAI_ONLY, "LLM_FALLBACK_MODEL_ID": "off"},
        {"LLM_PROVIDER": "scripted"},
    ],
)
def test_a_usable_or_absent_fallback_is_not_reported(
    environment: dict[str, str], caplog: pytest.LogCaptureFixture
) -> None:
    settings = assemble_app_settings(environment)

    with caplog.at_level(logging.WARNING, logger=LOGGER_NAME):
        assert report_unusable_fallback(settings) is None

    assert caplog.records == []
    assert usable_fallback_model_id(settings) == (
        settings.reply_speed.llm_fallback_model_id
    )


def test_the_router_never_reruns_a_turn_on_a_provider_without_a_key() -> None:
    anthropic = answering("from anthropic")
    routed = build_routing_llm_adapter(
        settings=assemble_app_settings(OPENAI_ONLY),
        openai_adapter=failing(),
        anthropic_adapter=anthropic,
        scripted_adapter=answering("scripted"),
        circuit_breaker=real_breaker(),
    )

    with pytest.raises(ExternalServiceError, match="OpenAI response failed"):
        routed.complete(build_request())
    assert anthropic.requests == []


def test_the_router_reruns_on_the_fallback_when_its_key_is_set() -> None:
    routed = build_routing_llm_adapter(
        settings=assemble_app_settings({**OPENAI_ONLY, "ANTHROPIC_API_KEY": "fake"}),
        openai_adapter=failing(),
        anthropic_adapter=answering("from anthropic"),
        scripted_adapter=answering("scripted"),
        circuit_breaker=real_breaker(),
    )

    response = routed.complete(build_request())

    assert str(response.text) == "from anthropic"
    assert response.fallback_model_id == FALLBACK_MODEL


def router_on(settings: AppSettings, scripted: ScriptedLlmAdapter) -> RoutingLlmAdapter:
    return build_routing_llm_adapter(
        settings=settings,
        openai_adapter=answering("from openai"),
        anthropic_adapter=answering("from anthropic"),
        scripted_adapter=scripted,
        circuit_breaker=real_breaker(),
    )


def test_production_never_routes_to_the_scripted_model() -> None:
    scripted = answering("a fixed sentence")
    production = router_on(assemble_app_settings(production_with({})), scripted)
    development = router_on(
        assemble_app_settings({"LLM_PROVIDER": "scripted"}), scripted
    )
    request = build_request(model_id=LlmModelId("scripted"))

    with pytest.raises(ExternalServiceError, match="No language-model provider"):
        production.complete(request)
    assert scripted.requests == []
    assert str(development.complete(request).text) == "a fixed sentence"
