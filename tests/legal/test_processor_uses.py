"""
Processor uses: every flow of personal data to a model provider is declared
once, and a process refuses to start in production (warns elsewhere) when
its settings send a flow to a provider the sub-processor list does not name
for that purpose on that day. The probe: an OpenAI deployment with
ANTHROPIC_API_KEY set judges the nightly quality sample with OpenAI until
the owners' notice of Anthropic as the quality judge has run its 30 days.
"""

import logging
from collections.abc import Mapping
from datetime import UTC, datetime

import pytest
from typed_time_provider import Microseconds, WallClock

from app.containers.app import AppContainer
from app.gateways.startup_checks import check_processor_uses
from app.registries.legal.processor_use_catalog import PROCESSOR_USES
from app.registries.legal.processor_use_registry import ProcessorUseRegistry
from app.registries.legal.subprocessor_entries_models import ANTHROPIC_QUALITY_FROM
from app.schemas.constants.legal import ProcessorFlow
from app.schemas.exceptions.application_errors import ValidationFailedError
from app.utilities.config_helpers.app_settings.app_settings_assembler import (
    assemble_app_settings,
)
from app.utilities.legal.processor_coverage import (
    configured_client_module,
    quality_judge_model_id,
)
from tests.e2e.workshop_container import replace_provider

OPENAI_WITH_ANTHROPIC_KEY: dict[str, str] = {
    "LLM_PROVIDER": "openai",
    "ANTHROPIC_API_KEY": "test-key-0000",
}
PRODUCTION: dict[str, str] = {"APP_ENV": "production", "ENCRYPTION_KEY": "x" * 32}
OTHER_JUDGE: dict[str, str] = {"QUALITY_SAMPLING_JUDGE_SAME_PROVIDER": "false"}
TODAY: str = "2026-10-05"


def container_on(environment: Mapping[str, str], day: str = TODAY) -> AppContainer:
    container = AppContainer()
    replace_provider(container.config.app_settings, assemble_app_settings(environment))
    moment = datetime.fromisoformat(f"{day}T12:00:00").replace(tzinfo=UTC)
    nanoseconds: int = int(moment.timestamp()) * 1_000_000_000
    replace_provider(
        container.time_provider.microsecond_wall_clock,
        WallClock(
            preferred_time_unit_type=Microseconds,
            unix_nanosecond_factory=lambda: nanoseconds,
        ),
    )
    return container


def test_every_flow_is_declared_once() -> None:
    declared = [use.flow for use in ProcessorUseRegistry().list_uses()]

    assert sorted(declared) == sorted(ProcessorFlow)
    with pytest.raises(ValueError, match="twice"):
        ProcessorUseRegistry((*PROCESSOR_USES, PROCESSOR_USES[0]))


def test_an_openai_deployment_with_an_anthropic_key_starts_by_default() -> None:
    container = container_on({**PRODUCTION, **OPENAI_WITH_ANTHROPIC_KEY})
    settings = container.config.app_settings()

    assert check_processor_uses(container) == []
    # The automatic checks are judged by Claude (the list covers it), the
    # real conversations by the assistant's own model.
    assert str(settings.llm_judge_model_id).startswith("claude-")
    assert quality_judge_model_id(settings) == settings.llm_model_id
    assert configured_client_module(ProcessorFlow.QUALITY_SAMPLING, settings) == (
        "openai"
    )


def test_production_refuses_anthropic_as_quality_judge_before_the_notice_ran() -> None:
    container = container_on({**PRODUCTION, **OPENAI_WITH_ANTHROPIC_KEY, **OTHER_JUDGE})

    with pytest.raises(ValidationFailedError, match="quality_sampling -> anthropic"):
        check_processor_uses(container)


def test_development_only_warns(caplog: pytest.LogCaptureFixture) -> None:
    container = container_on({**OPENAI_WITH_ANTHROPIC_KEY, **OTHER_JUDGE})

    with caplog.at_level(logging.WARNING, logger="app.gateways.startup_checks"):
        [uncovered] = check_processor_uses(container)

    assert uncovered.flow is ProcessorFlow.QUALITY_SAMPLING
    assert str(uncovered.client_module) == "anthropic"
    assert "customer_messages" in caplog.text
    assert "QUALITY_SAMPLING_JUDGE_SAME_PROVIDER" in caplog.text


def test_anthropic_judges_the_sample_once_its_notice_has_run() -> None:
    container = container_on(
        {**PRODUCTION, **OPENAI_WITH_ANTHROPIC_KEY, **OTHER_JUDGE},
        day=str(ANTHROPIC_QUALITY_FROM),
    )

    assert check_processor_uses(container) == []
    assert str(quality_judge_model_id(container.config.app_settings())).startswith(
        "claude-"
    )


def test_a_flow_that_is_off_reaches_nobody() -> None:
    settings = assemble_app_settings(
        {**OPENAI_WITH_ANTHROPIC_KEY, **OTHER_JUDGE, "QUALITY_SAMPLE_PERCENT": "0"}
    )
    scripted = assemble_app_settings({"LLM_PROVIDER": "scripted"})

    assert configured_client_module(ProcessorFlow.QUALITY_SAMPLING, settings) is None
    assert all(
        configured_client_module(flow, scripted) is None for flow in ProcessorFlow
    )


def test_an_anthropic_deployment_is_covered() -> None:
    container = container_on(
        {**PRODUCTION, "LLM_PROVIDER": "anthropic", "OPENAI_API_KEY": "test-0000"}
    )
    settings = container.config.app_settings()

    assert check_processor_uses(container) == []
    # Voice notes still go to OpenAI's speech-to-text, which the list covers.
    assert configured_client_module(ProcessorFlow.TRANSCRIPTION, settings) == "openai"
