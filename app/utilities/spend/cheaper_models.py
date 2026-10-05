"""
The cheaper model a business answers on past its soft spend limit.

It stays with the assistant's own provider: the conversation's stored
model turns are that provider's format, so a model of the same family can
continue them. SPEND_SOFT_LIMIT_MODEL_ID chooses it when it belongs to that
provider; otherwise each provider's small model: gpt-5-nano for OpenAI
(a fifth of gpt-5-mini's price), Claude Haiku 4.5 for Anthropic.
"""

from app.schemas.constants.assistants import LlmProvider
from app.schemas.typings.assistants.constrained_strings import LlmModelId
from app.utilities.conversations.llm_models import resolve_llm_provider

CHEAPER_MODEL_IDS: dict[LlmProvider, LlmModelId] = {
    LlmProvider.OPENAI: LlmModelId("gpt-5-nano"),
    LlmProvider.ANTHROPIC: LlmModelId("claude-haiku-4-5"),
    LlmProvider.SCRIPTED: LlmModelId("scripted"),
}


def cheaper_model_of(model_id: LlmModelId, configured: LlmModelId | None) -> LlmModelId:
    """The model to answer on instead of `model_id` past the soft limit."""

    provider: LlmProvider | None = resolve_llm_provider(model_id)
    if provider is None:
        return model_id

    if configured is not None and resolve_llm_provider(configured) is provider:
        return configured

    return CHEAPER_MODEL_IDS.get(provider, model_id)
