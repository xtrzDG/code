"""
LLM_*, OPENAI_*, AUTOTEST_TURN_LIMIT and SCRIPTED_LLM_LATENCY_MS: the
language model of the assistants and of their judge.
"""

from collections.abc import Mapping
from typing import TypedDict

from app.schemas.constants.assistants import LlmEffort, LlmProvider
from app.schemas.typings.assistants.constrained_integers import (
    AutotestTurnLimit,
    LlmCallTimeoutSeconds,
    LlmConcurrencyLimit,
    LlmMaxOutputTokens,
    LlmToolRoundLimit,
    ScriptedLlmLatencyMilliseconds,
)
from app.schemas.typings.assistants.constrained_strings import LlmModelId
from app.schemas.typings.channels.constrained_strings import PublicBaseUrl
from app.schemas.typings.platform.strings import PlatformIdentifier
from app.utilities.config_helpers.app_settings.environment_variable_readers import (
    optional_text,
    parse_setting,
    read_integer,
    read_text,
)

# The concept's choice: OpenAI gpt-5-mini in a project with EU data residency.
DEFAULT_LLM_PROVIDER: str = LlmProvider.OPENAI
DEFAULT_MODEL_IDS: dict[str, str] = {
    LlmProvider.OPENAI: "gpt-5-mini",
    LlmProvider.ANTHROPIC: "claude-opus-5-5",
    LlmProvider.SCRIPTED: "scripted",
}
# The judge of autotests and of real conversations comes from the other
# provider, so a model never grades its own family's answers: a strong
# Anthropic model for OpenAI deployments, the concept's OpenAI model for
# Anthropic ones; used when that provider's key is set, else the judge
# falls back to the deployment's own default model.
DEFAULT_JUDGE_MODEL_IDS: dict[str, tuple[str, str]] = {
    LlmProvider.OPENAI: ("claude-sonnet-5-5", "ANTHROPIC_API_KEY"),
    LlmProvider.ANTHROPIC: ("gpt-5-mini", "OPENAI_API_KEY"),
}
DEFAULT_OPENAI_BASE_URL: str = "https://eu.api.openai.com/v1"
# One model call of a customer chat (retried once) may take this long, so a
# slow provider costs a customer at most about a minute, not three.
DEFAULT_LLM_CALL_TIMEOUT_SECONDS: int = 25
# Model calls of one process at once: half the request threads
# (THREADPOOL_SIZE 64), so slow model calls never take every thread.
DEFAULT_LLM_MAX_CONCURRENCY: int = 32


class LlmSettingsSection(TypedDict):
    """The `AppSettings` fields of the language model."""

    llm_provider: LlmProvider
    llm_model_id: LlmModelId
    llm_judge_model_id: LlmModelId
    llm_summary_model_id: LlmModelId | None
    llm_chat_effort: LlmEffort
    llm_judge_effort: LlmEffort
    llm_max_output_tokens: LlmMaxOutputTokens
    llm_tool_round_limit: LlmToolRoundLimit
    llm_call_timeout_seconds: LlmCallTimeoutSeconds
    llm_max_concurrency: LlmConcurrencyLimit
    openai_base_url: PublicBaseUrl
    openai_project_id: PlatformIdentifier | None
    autotest_turn_limit: AutotestTurnLimit
    scripted_llm_latency_ms: ScriptedLlmLatencyMilliseconds


def read_llm_provider(environment_variables: Mapping[str, str]) -> LlmProvider:
    return LlmProvider(
        read_text(environment_variables, "LLM_PROVIDER", DEFAULT_LLM_PROVIDER)
    )


def read_llm_settings(
    environment_variables: Mapping[str, str],
    llm_provider: LlmProvider,
) -> LlmSettingsSection:
    """
    The chat model defaults to the provider's default model, the judge to
    the other provider's (see `read_judge_model_id`); call summaries use
    the chat model unless LLM_SUMMARY_MODEL_ID names a cheaper one.
    """

    default_model_id: str = DEFAULT_MODEL_IDS[llm_provider]
    return LlmSettingsSection(
        llm_provider=llm_provider,
        llm_model_id=LlmModelId(
            read_text(environment_variables, "LLM_MODEL_ID", default_model_id)
        ),
        llm_judge_model_id=read_judge_model_id(environment_variables, llm_provider),
        # The model of call summaries for staff; the chat model when unset.
        llm_summary_model_id=optional_text(
            environment_variables, "LLM_SUMMARY_MODEL_ID", LlmModelId
        ),
        llm_chat_effort=LlmEffort(
            read_text(environment_variables, "LLM_CHAT_EFFORT", LlmEffort.LOW)
        ),
        llm_judge_effort=LlmEffort(
            read_text(environment_variables, "LLM_JUDGE_EFFORT", LlmEffort.MEDIUM)
        ),
        llm_max_output_tokens=LlmMaxOutputTokens(
            read_integer(environment_variables, "LLM_MAX_OUTPUT_TOKENS", 16000)
        ),
        llm_tool_round_limit=LlmToolRoundLimit(
            read_integer(environment_variables, "LLM_TOOL_ROUND_LIMIT", 8)
        ),
        llm_call_timeout_seconds=parse_setting(
            "LLM_CALL_TIMEOUT_SECONDS",
            read_integer(
                environment_variables,
                "LLM_CALL_TIMEOUT_SECONDS",
                DEFAULT_LLM_CALL_TIMEOUT_SECONDS,
            ),
            LlmCallTimeoutSeconds,
        ),
        llm_max_concurrency=parse_setting(
            "LLM_MAX_CONCURRENCY",
            read_integer(
                environment_variables,
                "LLM_MAX_CONCURRENCY",
                DEFAULT_LLM_MAX_CONCURRENCY,
            ),
            LlmConcurrencyLimit,
        ),
        openai_base_url=PublicBaseUrl(
            read_text(environment_variables, "OPENAI_BASE_URL", DEFAULT_OPENAI_BASE_URL)
        ),
        openai_project_id=optional_text(
            environment_variables, "OPENAI_PROJECT_ID", PlatformIdentifier
        ),
        autotest_turn_limit=AutotestTurnLimit(
            read_integer(environment_variables, "AUTOTEST_TURN_LIMIT", 4)
        ),
        scripted_llm_latency_ms=parse_setting(
            "SCRIPTED_LLM_LATENCY_MS",
            read_integer(environment_variables, "SCRIPTED_LLM_LATENCY_MS", 0),
            ScriptedLlmLatencyMilliseconds,
        ),
    )


def read_judge_model_id(
    environment_variables: Mapping[str, str],
    llm_provider: LlmProvider,
) -> LlmModelId:
    """
    LLM_JUDGE_MODEL_ID, else the other provider's judge model when that
    provider's key is set, else the provider's own default model (the
    scripted provider judges with the scripted model).
    """

    own_default: str = DEFAULT_MODEL_IDS[llm_provider]
    # Which providers have a key (the SDKs read them; here only whether set).
    keyed: set[str] = {
        key_name
        for _, key_name in DEFAULT_JUDGE_MODEL_IDS.values()
        if environment_variables.get(key_name, "").strip() != ""
    }
    other: tuple[str, str] | None = DEFAULT_JUDGE_MODEL_IDS.get(llm_provider)
    default_judge: str = (
        other[0] if other is not None and other[1] in keyed else own_default
    )
    return LlmModelId(
        read_text(environment_variables, "LLM_JUDGE_MODEL_ID", default_judge)
    )
