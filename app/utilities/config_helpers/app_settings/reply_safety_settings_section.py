"""
LLM_VERIFIER_MODEL_ID and INJECTION_FLAG_LIMIT: the claim check and the
prompt-injection brake of the reply guard.
"""

from collections.abc import Mapping
from typing import TypedDict

from app.schemas.configurations.reply_safety_settings import (
    DEFAULT_INJECTION_FLAG_LIMIT,
    ReplySafetySettings,
)
from app.schemas.constants.assistants import LlmProvider
from app.schemas.typings.assistants.constrained_strings import LlmModelId
from app.schemas.typings.conversations.constrained_integers import (
    InjectionFlagLimit,
)
from app.utilities.config_helpers.app_settings.environment_variable_readers import (
    parse_setting,
    read_integer,
    read_text,
)

# The cheap model of the chat's own provider; the scripted model checks no
# claims (tests use a fake verifier).
DEFAULT_VERIFIER_MODEL_IDS: dict[LlmProvider, str] = {
    LlmProvider.OPENAI: "gpt-5-nano",
    LlmProvider.ANTHROPIC: "claude-haiku-4-5",
}
VERIFIER_OFF_VALUES: frozenset[str] = frozenset({"off", "none"})


class ReplySafetySettingsSection(TypedDict):
    """The `AppSettings` field of the reply guard's claim and injection checks."""

    reply_safety: ReplySafetySettings


def read_reply_safety_settings(
    environment_variables: Mapping[str, str],
    llm_provider: LlmProvider,
) -> ReplySafetySettingsSection:
    """
    LLM_VERIFIER_MODEL_ID defaults to the cheap model of the chat provider
    ("off" turns the claim check off).
    """

    return ReplySafetySettingsSection(
        reply_safety=ReplySafetySettings(
            llm_verifier_model_id=read_verifier_model_id(
                environment_variables, llm_provider
            ),
            injection_flag_limit=parse_setting(
                "INJECTION_FLAG_LIMIT",
                read_integer(
                    environment_variables,
                    "INJECTION_FLAG_LIMIT",
                    DEFAULT_INJECTION_FLAG_LIMIT,
                ),
                InjectionFlagLimit,
            ),
        )
    )


def read_verifier_model_id(
    environment_variables: Mapping[str, str],
    llm_provider: LlmProvider,
) -> LlmModelId | None:
    raw_value: str = read_text(
        environment_variables,
        "LLM_VERIFIER_MODEL_ID",
        DEFAULT_VERIFIER_MODEL_IDS.get(llm_provider, ""),
    )
    if raw_value == "" or raw_value.lower() in VERIFIER_OFF_VALUES:
        return None

    return parse_setting("LLM_VERIFIER_MODEL_ID", raw_value, LlmModelId)
