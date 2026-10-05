"""LLM_JUDGE_MODEL_ID defaults to the other provider's model when it has a key."""

import pytest

from app.utilities.config_helpers.app_settings.app_settings_assembler import (
    assemble_app_settings,
)

BOTH_KEYS: dict[str, str] = {
    "OPENAI_API_KEY": "test-openai-key",  # gitleaks:allow
    "ANTHROPIC_API_KEY": "test-anthropic-key",  # gitleaks:allow
}


@pytest.mark.parametrize(
    ("environment", "judge"),
    [
        ({"LLM_PROVIDER": "openai", **BOTH_KEYS}, "claude-sonnet-5-5"),
        ({"LLM_PROVIDER": "anthropic", **BOTH_KEYS}, "gpt-5-mini"),
        # Without the other provider's key the judge stays on its own.
        (
            {"LLM_PROVIDER": "openai", "OPENAI_API_KEY": "test-openai-key"},
            "gpt-5-mini",
        ),
        (
            {"LLM_PROVIDER": "anthropic", "ANTHROPIC_API_KEY": "test-key"},
            "claude-opus-5-5",
        ),
        ({"LLM_PROVIDER": "scripted", **BOTH_KEYS}, "scripted"),
        (
            {"LLM_PROVIDER": "openai", "LLM_JUDGE_MODEL_ID": "gpt-5", **BOTH_KEYS},
            "gpt-5",
        ),
    ],
)
def test_the_judge_comes_from_the_other_provider(
    environment: dict[str, str], judge: str
) -> None:
    settings = assemble_app_settings(environment)

    assert str(settings.llm_judge_model_id) == judge


def test_critical_samples_and_quality_sampling_read_the_environment() -> None:
    settings = assemble_app_settings(
        {
            "AUTOTEST_CRITICAL_SAMPLES": "3",
            "QUALITY_SAMPLE_PERCENT": "10",
            "QUALITY_SAMPLE_PER_BUSINESS": "7",
            "QUALITY_SAMPLE_BUDGET_CENTS": "250",
        }
    )
    defaults = assemble_app_settings({}).quality

    assert int(settings.quality.autotest_critical_samples) == 3
    assert int(settings.quality.sample_percent) == 10
    assert int(settings.quality.sample_per_business) == 7
    assert int(settings.quality.sample_budget_cents) == 250
    assert (
        int(defaults.autotest_critical_samples),
        int(defaults.sample_percent),
        int(defaults.sample_per_business),
        int(defaults.sample_budget_cents),
    ) == (2, 5, 20, 500)
