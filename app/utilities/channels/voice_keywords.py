"""
What the voice agent's speech recognition listens for (ASR keywords).

Callers name the business, a master, a room or a table, and the dishes and
services they want; those words are rare in everyday speech, so the speech
recognition is told to expect them. The list is the business's name, its
active resources and the titles of its top items (with their approved
titles in the agent's languages), one line each and without repeats.
"""

import re
from collections.abc import Iterator, Sequence

from app.schemas.constants.knowledge import KnowledgeAliasStatus, KnowledgeItemKind
from app.schemas.domain.knowledge import KnowledgeItemDocument
from app.schemas.domain.resources import ResourceDocument
from app.schemas.typings.businesses.strings import BusinessName
from app.schemas.typings.localization.constrained_strings import LanguageTag
from app.schemas.typings.voice.constrained_strings import AsrKeyword

# The items whose titles callers say: what is booked, ordered or bought.
# Questions and policies are sentences, not words to listen for.
NAMED_ITEM_KINDS: tuple[KnowledgeItemKind, ...] = (
    KnowledgeItemKind.SERVICE,
    KnowledgeItemKind.MENU_ITEM,
    KnowledgeItemKind.PACKAGE,
    KnowledgeItemKind.ROOM_TYPE,
    KnowledgeItemKind.VEHICLE,
    KnowledgeItemKind.PRODUCT,
)
MAX_KEYWORD_ITEMS: int = 50
MAX_ASR_KEYWORDS: int = 120
MAX_KEYWORD_LENGTH: int = 60
WHITESPACE: re.Pattern[str] = re.compile(r"\s+")
CONTROL_CHARACTERS: re.Pattern[str] = re.compile(r"[\x00-\x1f\x7f]")


def collect_asr_keywords(
    business_name: BusinessName,
    resources: Sequence[ResourceDocument],
    items: Sequence[KnowledgeItemDocument],
    languages: Sequence[LanguageTag],
) -> list[AsrKeyword]:
    """
    The keywords in order of importance: the business's name, its active
    resources, then its top MAX_KEYWORD_ITEMS items (services first, then
    dishes, packages, room types, vehicles and products, each kind by
    title), every item with its approved titles in `languages`. Phrases
    longer than MAX_KEYWORD_LENGTH are left out, repeats (ignoring case)
    too, and the list stops at MAX_ASR_KEYWORDS.
    """

    keywords: list[AsrKeyword] = []
    seen: set[str] = set()
    for text in candidate_texts(business_name, resources, items, languages):
        keyword: AsrKeyword | None = to_keyword(text)
        if keyword is None or str(keyword).casefold() in seen:
            continue

        seen.add(str(keyword).casefold())
        keywords.append(keyword)
        if len(keywords) == MAX_ASR_KEYWORDS:
            break

    return keywords


def candidate_texts(
    business_name: BusinessName,
    resources: Sequence[ResourceDocument],
    items: Sequence[KnowledgeItemDocument],
    languages: Sequence[LanguageTag],
) -> Iterator[str]:
    yield str(business_name)
    yield from (str(resource.name) for resource in resources if resource.is_active)
    wanted_languages: set[str] = {str(language).lower() for language in languages}
    for item in rank_items(items)[:MAX_KEYWORD_ITEMS]:
        yield str(item.title)
        yield from (
            str(alias.text)
            for alias in item.aliases
            if alias.status is KnowledgeAliasStatus.APPROVED
            and str(alias.language).lower() in wanted_languages
        )


def rank_items(items: Sequence[KnowledgeItemDocument]) -> list[KnowledgeItemDocument]:
    """Active named items, by kind (NAMED_ITEM_KINDS order) and title."""

    return sorted(
        (item for item in items if item.is_active and item.kind in NAMED_ITEM_KINDS),
        key=lambda item: (
            NAMED_ITEM_KINDS.index(item.kind),
            str(item.title).casefold(),
            str(item.title),
            str(item.id),
        ),
    )


def to_keyword(text: str) -> AsrKeyword | None:
    """One line with single spaces; None when empty or too long."""

    line: str = WHITESPACE.sub(" ", CONTROL_CHARACTERS.sub(" ", text)).strip()
    if not line or len(line) > MAX_KEYWORD_LENGTH:
        return None

    return AsrKeyword(line)
