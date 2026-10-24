"""Read the alias model's answer: usable aliases only, nothing invented."""

from collections.abc import Sequence
from typing import cast

from app.adapters.llm.website_extraction.website_item_parsing import (
    read_json_object,
)
from app.schemas.dto.knowledge_aliases import AliasSuggestionItem, SuggestedAlias
from app.schemas.typings.knowledge.constrained_strings import KnowledgeAliasText
from app.schemas.typings.localization.constrained_strings import LanguageTag
from app.utilities.knowledge.search_text import fold_words

MAX_ALIAS_LENGTH: int = 200


def parse_suggested_aliases(
    answer_text: str | None,
    items: Sequence[AliasSuggestionItem],
) -> list[SuggestedAlias] | None:
    """
    The aliases of the answer for the requested items and languages, in
    the items' order; None when the answer holds no {"items": [...]}
    object. An entry for an unknown item number, a language that was not
    asked for, an empty or overlong text, or a text that only repeats the
    title is skipped.
    """

    payload: dict[str, object] | None = read_json_object(answer_text or "")
    raw_items: object = None if payload is None else payload.get("items")
    if not isinstance(raw_items, list):
        return None

    by_number: dict[int, dict[str, object]] = {}
    for raw_item in cast(list[object], raw_items):
        if not isinstance(raw_item, dict):
            continue

        entry: dict[str, object] = cast(dict[str, object], raw_item)
        number: object = entry.get("n")
        if isinstance(number, int) and not isinstance(number, bool):
            by_number.setdefault(number, entry)

    aliases: list[SuggestedAlias] = []
    for number, item in enumerate(items, start=1):
        entry_found: dict[str, object] | None = by_number.get(number)
        if entry_found is not None:
            aliases.extend(read_item_aliases(item, entry_found.get("aliases")))

    return aliases


def read_item_aliases(
    item: AliasSuggestionItem, raw_aliases: object
) -> list[SuggestedAlias]:
    """The usable aliases of one item's answer entry."""

    if not isinstance(raw_aliases, dict):
        return []

    texts: dict[object, object] = cast(dict[object, object], raw_aliases)
    folded_title: str = fold_words(item.title)
    aliases: list[SuggestedAlias] = []
    for language in item.target_languages:
        text: str | None = clean_alias_text(texts.get(str(language)))
        if text is None or fold_words(text) == folded_title:
            continue

        aliases.append(
            SuggestedAlias(
                item_id=item.item_id,
                language=LanguageTag(str(language)),
                text=KnowledgeAliasText(text),
            )
        )

    return aliases


def clean_alias_text(raw_text: object) -> str | None:
    """One line without control characters or quotes around it, or None."""

    if not isinstance(raw_text, str):
        return None

    printable: str = "".join(
        " " if ord(character) < 0x20 or ord(character) == 0x7F else character
        for character in raw_text
    )
    text: str = " ".join(printable.split()).strip().strip("\"'«»“”„")
    text = text.strip()
    if text == "" or len(text) > MAX_ALIAS_LENGTH:
        return None

    return text
