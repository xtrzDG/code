"""
MESSAGE_COALESCE_SECONDS, CHAT_TURN_DEADLINE_SECONDS and
LLM_FALLBACK_MODEL_ID: fast, resilient replies in the messaging channels.
"""

from collections.abc import Mapping
from typing import TypedDict

from app.schemas.configurations.reply_speed_settings import (
    DEFAULT_CHAT_TURN_DEADLINE_SECONDS,
    DEFAULT_MESSAGE_COALESCE_SECONDS,
    ReplySpeedSettings,
)
from app.schemas.constants.assistants import LlmProvider
from app.schemas.typings.assistants.constrained_strings import LlmModelId
from app.schemas.typings.conversations.constrained_integers import (
    ChatTurnDeadlineSeconds,
    MessageCoalesceSeconds,
)
from app.utilities.config_helpers.app_settings.environment_variable_readers import (
    parse_setting,
    read_integer,
    read_text,
)

# The model of the other provider a chat falls back to when its own
# provider fails: a strong Anthropic model for OpenAI deployments and the
# concept's OpenAI default for Anthropic ones. The scripted model has none.
DEFAULT_FALLBACK_MODEL_IDS: dict[LlmProvider, str] = {
    LlmProvider.OPENAI: "claude-sonnet-5-5",
    LlmProvider.ANTHROPIC: "gpt-5-mini",
}
FALLBACK_OFF_VALUES: frozenset[str] = frozenset({"off", "none"})


class ReplySpeedSettingsSection(TypedDict):
    """The `AppSettings` field of reply speed and failover."""

    reply_speed: ReplySpeedSettings


def read_reply_speed_settings(
    environment_variables: Mapping[str, str],
    llm_provider: LlmProvider,
) -> ReplySpeedSettingsSection:
    """
    LLM_FALLBACK_MODEL_ID defaults to the other provider's model ("off"
    turns failover off); it is only tried when that provider has its key.
    """

    return ReplySpeedSettingsSection(
        reply_speed=ReplySpeedSettings(
            message_coalesce_seconds=parse_setting(
                "MESSAGE_COALESCE_SECONDS",
                read_integer(
                    environment_variables,
                    "MESSAGE_COALESCE_SECONDS",
                    DEFAULT_MESSAGE_COALESCE_SECONDS,
                ),
                MessageCoalesceSeconds,
            ),
            chat_turn_deadline_seconds=parse_setting(
                "CHAT_TURN_DEADLINE_SECONDS",
                read_integer(
                    environment_variables,
                    "CHAT_TURN_DEADLINE_SECONDS",
                    DEFAULT_CHAT_TURN_DEADLINE_SECONDS,
                ),
                ChatTurnDeadlineSeconds,
            ),
            llm_fallback_model_id=read_fallback_model_id(
                environment_variables, llm_provider
            ),
        )
    )


def read_fallback_model_id(
    environment_variables: Mapping[str, str],
    llm_provider: LlmProvider,
) -> LlmModelId | None:
    raw_value: str = read_text(
        environment_variables,
        "LLM_FALLBACK_MODEL_ID",
        DEFAULT_FALLBACK_MODEL_IDS.get(llm_provider, ""),
    )
    if raw_value == "" or raw_value.lower() in FALLBACK_OFF_VALUES:
        return None

    return parse_setting("LLM_FALLBACK_MODEL_ID", raw_value, LlmModelId)
