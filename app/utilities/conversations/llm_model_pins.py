"""
The model versions the platform calls by default, pinned (AI-12).

A provider's floating alias ("gpt-5-mini", "claude-haiku-4-5", anything
"-latest") moves to a new model when the provider releases one, so the
assistant would change its behaviour without a prompt, eval or deploy on
our side. Every default model id is therefore a dated snapshot, or a model
id the provider publishes without a date and never repoints (Claude Opus
5.5, Claude Sonnet 5.5). The offline `scripted` model of development and
tests is not a provider model and stays as it is.
`tests/platform/test_model_pins.py` keeps the defaults pinned, and
`docs/security/ai-components.md` lists every pin.
"""

OPENAI_GPT_5_MINI: str = "gpt-5-mini-2025-08-07"
OPENAI_GPT_5_NANO: str = "gpt-5-nano-2025-08-07"
ANTHROPIC_OPUS_5_5: str = "claude-opus-5-5"
ANTHROPIC_SONNET_5_5: str = "claude-sonnet-5-5"
ANTHROPIC_HAIKU_4_5: str = "claude-haiku-4-5-20251001"

# Floating aliases and the dated snapshot each one pointed to when pinned.
FLOATING_MODEL_ALIASES: dict[str, str] = {
    "gpt-5": "gpt-5-2025-08-07",
    "gpt-5-mini": OPENAI_GPT_5_MINI,
    "gpt-5-nano": OPENAI_GPT_5_NANO,
    "claude-haiku-4-5": ANTHROPIC_HAIKU_4_5,
    "claude-sonnet-4-5": "claude-sonnet-4-5-20250929",
    "claude-opus-4-5": "claude-opus-4-5-20251101",
}
LATEST_ALIAS_SUFFIX: str = "latest"


def pinned_snapshot_of(model_id: str) -> str | None:
    """
    The dated snapshot to name instead of a floating alias; None when the
    id is already pinned. A "-latest" id has no fixed snapshot, so it
    answers the id itself (the caller reports it as unpinned).
    """

    if model_id.endswith(LATEST_ALIAS_SUFFIX):
        return model_id

    return FLOATING_MODEL_ALIASES.get(model_id)


def is_pinned_model_id(model_id: str) -> bool:
    """True when `model_id` names one fixed model version."""

    return pinned_snapshot_of(model_id) is None
