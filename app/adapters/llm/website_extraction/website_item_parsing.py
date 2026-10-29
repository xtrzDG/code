"""Read the website reader's answer: unusable items are skipped and counted."""

import json
from collections.abc import Collection
from typing import cast

from app.adapters.llm.menu_extraction.menu_item_parsing import read_menu_item
from app.schemas.dto.menu_import import ExtractedMenuItem

MAX_ITEMS_PER_PAGE: int = 60


def parse_website_items(
    answer_text: str | None,
    allowed_kinds: Collection[str],
) -> tuple[list[ExtractedMenuItem], int] | None:
    """
    The usable items of the answer and how many were skipped (an empty
    title, a kind the business does not keep, too many items); None when
    the answer holds no {"items": [...]} object.
    """

    payload: dict[str, object] | None = read_json_object(answer_text or "")
    raw_items: object = None if payload is None else payload.get("items")
    if not isinstance(raw_items, list):
        return None

    items: list[ExtractedMenuItem] = []
    skipped: int = 0
    for raw_item in cast(list[object], raw_items):
        item: ExtractedMenuItem | None = (
            read_menu_item(cast(dict[str, object], raw_item), allowed_kinds)
            if isinstance(raw_item, dict)
            else None
        )
        if item is None or len(items) >= MAX_ITEMS_PER_PAGE:
            skipped += 1
        else:
            items.append(item)

    return items, skipped


def read_json_object(text: str) -> dict[str, object] | None:
    """The outermost JSON object of a text (prose or code fences around it)."""

    start: int = text.find("{")
    end: int = text.rfind("}")
    if start == -1 or end <= start:
        return None

    try:
        decoded: object = json.loads(text[start : end + 1])
    except json.JSONDecodeError:
        return None

    if not isinstance(decoded, dict):
        return None

    return {
        str(key): value for key, value in cast(dict[object, object], decoded).items()
    }
