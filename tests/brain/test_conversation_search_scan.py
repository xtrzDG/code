"""A search looks at a bounded number of conversations per request."""

from typing import Any

import pytest

from app.use_cases.conversations.feed import feed_search_scan
from tests.brain.brain_world import build_world
from tests.brain.conversation_cabinet_helpers import Cabinet, seed_feed
from tests.brain.scripted_turns import say, scripted


def walk(cabinet: Cabinet, **params: str) -> list[dict[str, Any]]:
    pages: list[dict[str, Any]] = [cabinet.feed(**params)]
    while pages[-1]["next_cursor"] is not None:
        pages.append(cabinet.feed(cursor=pages[-1]["next_cursor"], **params))

    return pages


def test_a_search_goes_on_where_the_scan_budget_ended(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    world = build_world(scripted(*(say(f"Answer {n}") for n in range(4))))
    seed_feed(world)
    cabinet = Cabinet(world)
    monkeypatch.setattr(feed_search_scan, "SEARCH_BATCH", 1)
    monkeypatch.setattr(feed_search_scan, "SEARCH_SCAN_LIMIT", 1)

    pages = walk(cabinet, search="столик")

    # Giorgi and José are newer and do not match; each request looks at one
    # conversation, the last one finds that nothing older is left.
    assert [[row["contact_name"] for row in page["items"]] for page in pages] == [
        [],
        [],
        ["Ниноʼ Беридзе"],
        [],
    ]


def test_a_search_page_stops_at_its_size(monkeypatch: pytest.MonkeyPatch) -> None:
    world = build_world(scripted(*(say(f"Answer {n}") for n in range(4))))
    seed_feed(world)
    cabinet = Cabinet(world)
    monkeypatch.setattr(feed_search_scan, "SEARCH_BATCH", 2)

    pages = walk(cabinet, search="answer", limit="1")

    assert [[row["contact_name"] for row in page["items"]] for page in pages] == [
        ["Giorgi"],
        ["José"],
        ["Ниноʼ Беридзе"],
    ]
