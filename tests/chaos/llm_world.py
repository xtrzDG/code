"""
The LLM game day's restaurant: the e2e restaurant whose published version
runs on OpenAI's model (the fake provider answers for it), in processes
that have no other provider to fail over to.
"""

from tests.chaos.chaos_world import ChaosWorld

CHAT_MODEL_ID: str = "gpt-5-mini"
# One provider and nothing to fail over to: the single-provider setup.
OPENAI_ONLY: dict[str, str] = {
    "LLM_PROVIDER": "openai",
    "LLM_MODEL_ID": CHAT_MODEL_ID,
    "LLM_FALLBACK_MODEL_ID": "off",
    "LLM_VERIFIER_MODEL_ID": "off",
    # A model call gives up after 2 s (and is retried once): the 30-second
    # provider costs the game day seconds, not minutes.
    "LLM_CALL_TIMEOUT_SECONDS": "2",
    # The watchdog would see the moved clock before the worker's next pulse.
    "PIPELINE_WATCHDOG_SECONDS": "0",
}


def run_on_openai(world: ChaosWorld) -> None:
    """The restaurant was published offline; its version now names gpt-5-mini."""

    world.execute(
        "update workshop.assistant_versions set document = "
        "jsonb_set(document, '{model_id}', to_jsonb(%s::text))",
        CHAT_MODEL_ID,
    )
