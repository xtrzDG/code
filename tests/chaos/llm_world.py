"""
The LLM game day's restaurant: the e2e restaurant whose published version
runs on OpenAI's model (the fake provider answers for it), and website
visitors who write in the widget and read the assistant's answers.
"""

from typing import Any, cast

import httpx

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


def session_key(index: int) -> str:
    return f"visitor_llm_game_day_{index:03d}"


def visitor_writes(world: ChaosWorld, api_url: str, index: int, text: str) -> None:
    """Visitor `index` writes in the website widget (answered by the worker)."""

    response = httpx.post(
        f"{api_url}/v1/widget/{world.restaurant.business_id}/messages",
        json={"session_key": session_key(index), "text": text},
        timeout=30,
    )
    assert response.status_code == 202, response.text


def widget_page(
    world: ChaosWorld, api_url: str, index: int, after: str
) -> dict[str, Any]:
    response = httpx.get(
        f"{api_url}/v1/widget/{world.restaurant.business_id}/messages",
        headers={"X-Widget-Session-Key": session_key(index)},
        params={"after": after},
        timeout=10,
    )
    assert response.status_code == 200, response.text
    return cast(dict[str, Any], response.json())


def assistant_answers(world: ChaosWorld, api_url: str, index: int) -> list[str]:
    """
    What the assistant wrote to visitor `index` after their latest message,
    read as the widget does: a poll without a position learns it, the next
    one reads what came after it.
    """

    position = str(widget_page(world, api_url, index, "")["cursor"] or "")
    return [
        str(item["text"])
        for item in widget_page(world, api_url, index, position)["items"]
        if item["author"] == "assistant"
    ]
