"""LLM_*, OPENAI_* and AUTOTEST_TURN_LIMIT: the language model of the assistants."""

from collections.abc import Mapping
from typing import TypedDict

from app.schemas.constants.assistants import LlmEffort, LlmProvider
from app.schemas.typings.assistants.constrained_integers import (
    AutotestTurnLimit,
    LlmMaxOutputTokens,
    LlmToolRoundLimit,
)
from app.schemas.typings.assistants.constrained_strings import LlmModelId
from app.schemas.typings.channels.constrained_strings import PublicBaseUrl
from app.schemas.typings.platform.strings import PlatformIdentifier
from app.utilities.config_helpers.app_settings.environment_variable_readers import (
    optional_text,
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
DEFAULT_OPENAI_BASE_URL: str = "https://eu.api.openai.com/v1"


class LlmSettingsSection(TypedDict):
    """The `AppSettings` fields of the language model."""

    llm_provider: LlmProvider
    llm_model_id: LlmModelId
    llm_judge_model_id: LlmModelId
    llm_chat_effort: LlmEffort
    llm_judge_effort: LlmEffort
    llm_max_output_tokens: LlmMaxOutputTokens
    llm_tool_round_limit: LlmToolRoundLimit
    openai_base_url: PublicBaseUrl
    openai_project_id: PlatformIdentifier | None
    autotest_turn_limit: AutotestTurnLimit


def read_llm_provider(environment_variables: Mapping[str, str]) -> LlmProvider:
    return LlmProvider(
        read_text(environment_variables, "LLM_PROVIDER", DEFAULT_LLM_PROVIDER)
    )


def read_llm_settings(
    environment_variables: Mapping[str, str],
    llm_provider: LlmProvider,
) -> LlmSettingsSection:
    """Both models default to the provider's default model."""

    default_model_id: str = DEFAULT_MODEL_IDS[llm_provider]
    return LlmSettingsSection(
        llm_provider=llm_provider,
        llm_model_id=LlmModelId(
            read_text(environment_variables, "LLM_MODEL_ID", default_model_id)
        ),
        llm_judge_model_id=LlmModelId(
            read_text(environment_variables, "LLM_JUDGE_MODEL_ID", default_model_id)
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
        openai_base_url=PublicBaseUrl(
            read_text(environment_variables, "OPENAI_BASE_URL", DEFAULT_OPENAI_BASE_URL)
        ),
        openai_project_id=optional_text(
            environment_variables, "OPENAI_PROJECT_ID", PlatformIdentifier
        ),
        autotest_turn_limit=AutotestTurnLimit(
            read_integer(environment_variables, "AUTOTEST_TURN_LIMIT", 4)
        ),
    )
