"""
Which configured models can be called: a model of OpenAI or Anthropic needs
its provider's API key (OPENAI_API_KEY, ANTHROPIC_API_KEY), which the SDKs
read themselves; the settings note which keys are set
(`AppSettings.keyed_llm_providers`).
"""

import logging

from app.schemas.configurations.app_settings import AppSettings
from app.schemas.constants.assistants import LlmProvider
from app.schemas.typings.assistants.constrained_strings import LlmModelId
from app.schemas.typings.platform.constrained_strings import EnvironmentVariableName
from app.utilities.config_helpers.app_settings.llm_settings_section import (
    LLM_PROVIDER_KEY_VARIABLES,
)
from app.utilities.conversations.llm_models import resolve_llm_provider

LOGGER: logging.Logger = logging.getLogger(__name__)


def missing_key_variable(
    settings: AppSettings, model_id: LlmModelId
) -> EnvironmentVariableName | None:
    """
    The API key variable a model's provider needs and this environment
    lacks; None when the key is set or the model needs none (the scripted
    model, or an id no provider serves).
    """

    provider: LlmProvider | None = resolve_llm_provider(model_id)
    key_variable: str | None = (
        None if provider is None else LLM_PROVIDER_KEY_VARIABLES.get(provider)
    )
    if key_variable is None or provider in settings.keyed_llm_providers:
        return None

    return EnvironmentVariableName(key_variable)


def usable_fallback_model_id(settings: AppSettings) -> LlmModelId | None:
    """
    LLM_FALLBACK_MODEL_ID when its provider's key is set; None otherwise,
    so a failing chat is never rerun on a provider that would refuse it.
    """

    fallback: LlmModelId | None = settings.reply_speed.llm_fallback_model_id
    if fallback is None or missing_key_variable(settings, fallback) is not None:
        return None

    return fallback


def report_unusable_fallback(settings: AppSettings) -> LlmModelId | None:
    """
    At startup: one warning when the fallback model is skipped because its
    provider has no key (failover is then off). Returns the skipped model.
    """

    fallback: LlmModelId | None = settings.reply_speed.llm_fallback_model_id
    key_variable: EnvironmentVariableName | None = (
        None if fallback is None else missing_key_variable(settings, fallback)
    )
    if fallback is None or key_variable is None:
        return None

    LOGGER.warning(
        "LLM_FALLBACK_MODEL_ID %s is skipped: %s is not set, so a chat whose "
        "model fails is not rerun on another provider. Set %s, or "
        "LLM_FALLBACK_MODEL_ID=off.",
        fallback,
        key_variable,
        key_variable,
    )
    return fallback
