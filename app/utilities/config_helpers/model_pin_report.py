"""
At startup: one warning for every configured model that names a floating
alias (AI-12). The defaults are pinned versions
(`app/utilities/conversations/llm_model_pins.py`); an environment variable
that names "gpt-5-mini" or "claude-haiku-4-5" instead lets the provider
change the assistant's model without a deploy. It is a warning, not a
refusal: a running deployment keeps answering, and the log names the pinned
version to set.
"""

import logging

from app.schemas.configurations.app_settings import AppSettings
from app.schemas.typings.assistants.constrained_strings import LlmModelId
from app.utilities.config_helpers.production.model_requirements import (
    configured_models,
)
from app.utilities.conversations.llm_model_pins import (
    is_pinned_model_id,
    pinned_snapshot_of,
)

LOGGER: logging.Logger = logging.getLogger(__name__)


def report_floating_models(settings: AppSettings) -> list[LlmModelId]:
    """Warn once per configured floating alias; returns those model ids."""

    models: list[tuple[str, LlmModelId]] = configured_models(settings)
    fallback: LlmModelId | None = settings.reply_speed.llm_fallback_model_id
    if fallback is not None:
        models.append(("LLM_FALLBACK_MODEL_ID", fallback))

    floating: list[LlmModelId] = []
    for variable_name, model_id in models:
        if is_pinned_model_id(str(model_id)):
            continue

        floating.append(model_id)
        LOGGER.warning(
            "%s=%s is a floating alias the provider can point to a new model "
            "at any time: name a pinned version (e.g. %s, see "
            "docs/security/ai-components.md).",
            variable_name,
            model_id,
            pinned_snapshot_of(str(model_id)),
        )

    return floating
