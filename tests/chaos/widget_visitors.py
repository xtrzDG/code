"""
Website visitors of a game day: they write in the restaurant's widget and
read the assistant's answers as the widget does (a poll without a
position learns it, the next one reads what came after it).
"""

from typing import Any, cast

import httpx

from tests.chaos.chaos_world import ChaosWorld


def session_key(index: int) -> str:
    return f"visitor_game_day_{index:03d}"


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
