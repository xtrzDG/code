"""
Every model the platform calls by default is a pinned version, never a
floating alias that a provider repoints (AI-12); the offline scripted model
of development and tests stays.
"""

import logging
import re
from pathlib import Path

import pytest

from app.containers.factories import DEFAULT_MENU_EXTRACTION_MODEL_ID
from app.registries.localization.voice_profile_registry import VOICE_PROFILES
from app.schemas.configurations.embedding_settings import DEFAULT_EMBEDDINGS_MODEL_ID
from app.schemas.configurations.media_settings import DEFAULT_TRANSCRIPTION_MODEL_ID
from app.schemas.configurations.voice_agent_settings import DEFAULT_VOICE_AGENT_LLM
from app.schemas.constants.assistants import LlmProvider
from app.schemas.typings.assistants.constrained_strings import LlmModelId
from app.schemas.typings.conversations.constrained_integers import LlmTokenCount
from app.utilities.assembly.llm_costs import DEFAULT_LLM_TOKEN_PRICES, estimate_llm_cost
from app.utilities.assembly.voice_agents import VOICE_AGENT_REVISION
from app.utilities.config_helpers.app_settings.app_settings_assembler import (
    assemble_app_settings,
)
from app.utilities.config_helpers.app_settings.llm_settings_section import (
    DEFAULT_JUDGE_MODEL_IDS,
    DEFAULT_MODEL_IDS,
)
from app.utilities.config_helpers.app_settings.reply_safety_settings_section import (
    DEFAULT_VERIFIER_MODEL_IDS,
)
from app.utilities.config_helpers.app_settings.reply_speed_settings_section import (
    DEFAULT_FALLBACK_MODEL_IDS,
)
from app.utilities.config_helpers.model_pin_report import report_floating_models
from app.utilities.conversations.llm_model_pins import (
    FLOATING_MODEL_ALIASES,
    is_pinned_model_id,
    pinned_snapshot_of,
)
from app.utilities.conversations.llm_models import (
    find_anthropic_model_features,
    find_llm_token_price,
)
from app.utilities.quality.quality_costs import price_of
from app.utilities.spend.cheaper_models import CHEAPER_MODEL_IDS

REPOSITORY: Path = Path(__file__).resolve().parents[2]
BOTH_KEYS: dict[str, str] = {
    "OPENAI_API_KEY": "test-openai-key",  # gitleaks:allow
    "ANTHROPIC_API_KEY": "test-anthropic-key",  # gitleaks:allow
}
# A model id written as a setting's value in a deploy or CI file.
CONFIGURED_MODEL: re.Pattern[str] = re.compile(
    r"(?:MODEL_ID|model|judge)[ \t]*[:=][ \t]*[\"']?([a-z0-9][a-z0-9.\-]+)",
    re.IGNORECASE,
)
PIN_REPORT_LOGGER: str = "app.utilities.config_helpers.model_pin_report"
CONFIG_FILES: tuple[str, ...] = (
    ".env.example",
    "render.yaml",
    "render.staging.yaml",
    ".github/workflows/evals-nightly.yml",
)


def default_model_ids() -> list[str]:
    defaults: list[str] = [
        *DEFAULT_MODEL_IDS.values(),
        *(model for model, _ in DEFAULT_JUDGE_MODEL_IDS.values()),
        *DEFAULT_FALLBACK_MODEL_IDS.values(),
        *DEFAULT_VERIFIER_MODEL_IDS.values(),
        *(str(model) for model in CHEAPER_MODEL_IDS.values()),
        str(DEFAULT_MENU_EXTRACTION_MODEL_ID),
    ]
    return defaults


def test_every_default_model_is_a_pinned_version() -> None:
    unpinned = [model for model in default_model_ids() if not is_pinned_model_id(model)]

    assert unpinned == []
    assert "scripted" in default_model_ids()


@pytest.mark.parametrize("provider", ["openai", "anthropic", "scripted"])
def test_assembled_settings_call_only_pinned_models(provider: str) -> None:
    settings = assemble_app_settings({"LLM_PROVIDER": provider, **BOTH_KEYS})
    models = [
        settings.llm_model_id,
        settings.llm_judge_model_id,
        settings.reply_safety.llm_verifier_model_id,
        settings.reply_speed.llm_fallback_model_id,
    ]

    assert [
        str(m) for m in models if m is not None and not is_pinned_model_id(str(m))
    ] == []


@pytest.mark.parametrize(
    ("model_id", "snapshot"),
    [
        ("gpt-5-mini", "gpt-5-mini-2025-08-07"),
        ("claude-haiku-4-5", "claude-haiku-4-5-20251001"),
        ("gpt-5-chat-latest", "gpt-5-chat-latest"),
        ("claude-opus-5-5", None),
        ("gpt-5-mini-2025-08-07", None),
        ("scripted", None),
    ],
)
def test_aliases_are_told_apart_from_pins(model_id: str, snapshot: str | None) -> None:
    assert pinned_snapshot_of(model_id) == snapshot


def test_a_pinned_snapshot_keeps_its_alias_price_and_features() -> None:
    for alias, snapshot in FLOATING_MODEL_ALIASES.items():
        assert find_llm_token_price(LlmModelId(snapshot)) == find_llm_token_price(
            LlmModelId(alias)
        )
        if alias.startswith("claude-"):
            assert find_anthropic_model_features(
                snapshot
            ) == find_anthropic_model_features(alias)


def test_a_pinned_default_keeps_its_list_price_where_ids_must_match() -> None:
    """
    The autotest estimate and the quality judge's nightly budget look a
    model's list price up by its exact id: a pinned default costs what its
    alias costs there, never nothing (the estimate) or the dearest model's
    price (the budget).
    """

    tokens = (LlmTokenCount(1_000), LlmTokenCount(500))
    alias_of: dict[str, str] = {
        snapshot: alias for alias, snapshot in FLOATING_MODEL_ALIASES.items()
    }
    for model_id in default_model_ids():
        if model_id == "scripted":
            continue

        pinned = LlmModelId(model_id)
        aliased = LlmModelId(alias_of.get(model_id, model_id))
        assert estimate_llm_cost(DEFAULT_LLM_TOKEN_PRICES, pinned, *tokens) > 0
        assert estimate_llm_cost(
            DEFAULT_LLM_TOKEN_PRICES, pinned, *tokens
        ) == estimate_llm_cost(DEFAULT_LLM_TOKEN_PRICES, aliased, *tokens)
        assert price_of(DEFAULT_LLM_TOKEN_PRICES, pinned).model_id == pinned


@pytest.mark.parametrize("relative_path", CONFIG_FILES)
def test_deploy_and_ci_files_name_no_floating_alias(relative_path: str) -> None:
    text = (REPOSITORY / relative_path).read_text(encoding="utf-8")
    named = [match.group(1) for match in CONFIGURED_MODEL.finditer(text)]

    assert [model for model in named if not is_pinned_model_id(model)] == []


def test_a_configured_floating_alias_is_reported_at_startup(
    caplog: pytest.LogCaptureFixture,
) -> None:
    floating = assemble_app_settings(
        {
            **BOTH_KEYS,
            "LLM_SUMMARY_MODEL_ID": "gpt-5-nano",
            "LLM_FALLBACK_MODEL_ID": "claude-sonnet-4-5",
        }
    )
    pinned = assemble_app_settings(BOTH_KEYS)

    with caplog.at_level(logging.WARNING, logger=PIN_REPORT_LOGGER):
        reported = report_floating_models(floating)
    assert report_floating_models(pinned) == []

    assert reported == ["gpt-5-nano", "claude-sonnet-4-5"]
    [summary, fallback] = [record.getMessage() for record in caplog.records]
    assert summary.startswith("LLM_SUMMARY_MODEL_ID=gpt-5-nano is a floating alias")
    assert "gpt-5-nano-2025-08-07" in summary
    assert "claude-sonnet-4-5-20250929" in fallback


def test_the_scripted_provider_keeps_its_offline_model() -> None:
    settings = assemble_app_settings({"LLM_PROVIDER": LlmProvider.SCRIPTED.value})

    assert settings.llm_model_id == "scripted"


def test_the_component_inventory_lists_every_pin() -> None:
    inventory = (REPOSITORY / "docs/security/ai-components.md").read_text(
        encoding="utf-8"
    )
    pins: set[str] = {
        *default_model_ids(),
        DEFAULT_TRANSCRIPTION_MODEL_ID,
        DEFAULT_EMBEDDINGS_MODEL_ID,
        DEFAULT_VOICE_AGENT_LLM,
        *(str(profile.tts_model) for profile in VOICE_PROFILES.values()),
    }

    assert [pin for pin in sorted(pins) if f"`{pin}`" not in inventory] == []
    assert f"`VOICE_AGENT_REVISION` (now {int(VOICE_AGENT_REVISION)}" in inventory
