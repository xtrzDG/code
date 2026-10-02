"""
The fact table of the instruction stays short for a big catalog.

A menu or price list of hundreds of items would make every model call long
and slow and drown the rules. Above KNOWLEDGE_ITEM_LIMIT knowledge items
the instruction lists an overview (how many items of each kind and their
categories, from the item tags) and the first LISTED_KNOWLEDGE_ITEMS items
(questions and policies come first in the table); the model finds the rest
with search_knowledge and get_price. The version keeps its full fact table:
the invented-numbers guard and the cabinet still see every row.
"""

from collections import Counter
from collections.abc import Sequence

from app.schemas.constants.knowledge import KnowledgeItemKind
from app.schemas.domain.assistants import BusinessFact
from app.schemas.domain.knowledge import KnowledgeItemDocument
from app.schemas.typings.profiles.constrained_strings import FactKey
from app.schemas.typings.profiles.strings import FactLabel, FactValue
from app.utilities.assembly.fact_descriptions import KNOWLEDGE_KIND_LABELS

KNOWLEDGE_ITEM_LIMIT: int = 80
LISTED_KNOWLEDGE_ITEMS: int = 30
MAX_CATEGORY_NAMES: int = 12
KNOWLEDGE_KIND_PLURALS: dict[KnowledgeItemKind, str] = {
    KnowledgeItemKind.FAQ: "questions",
    KnowledgeItemKind.POLICY: "policies",
    KnowledgeItemKind.MENU_ITEM: "menu items",
    KnowledgeItemKind.SERVICE: "services",
    KnowledgeItemKind.ROOM_TYPE: "room types",
    KnowledgeItemKind.PACKAGE: "packages",
    KnowledgeItemKind.VEHICLE: "vehicles",
    KnowledgeItemKind.PRODUCT: "products",
}


def limit_knowledge_facts(
    facts: Sequence[BusinessFact],
    knowledge_items: Sequence[KnowledgeItemDocument],
) -> list[BusinessFact]:
    """
    The rows the instruction lists: all of them up to KNOWLEDGE_ITEM_LIMIT
    knowledge items, else the other rows with the overview and the first
    LISTED_KNOWLEDGE_ITEMS knowledge rows where the knowledge rows began.
    """

    active_items: list[KnowledgeItemDocument] = [
        item for item in knowledge_items if item.is_active
    ]
    knowledge_labels: set[str] = {describe_item_label(item) for item in active_items}
    knowledge_positions: list[int] = [
        position
        for position, fact in enumerate(facts)
        if is_knowledge_fact(fact, knowledge_labels)
    ]
    if len(knowledge_positions) <= KNOWLEDGE_ITEM_LIMIT:
        return list(facts)

    listed_positions: set[int] = set(knowledge_positions[:LISTED_KNOWLEDGE_ITEMS])
    all_positions: set[int] = set(knowledge_positions)
    limited: list[BusinessFact] = []
    for position, fact in enumerate(facts):
        if position == knowledge_positions[0]:
            limited.extend(build_overview_facts(active_items, len(knowledge_positions)))

        if position not in all_positions or position in listed_positions:
            limited.append(fact)

    return limited


def describe_item_label(item: KnowledgeItemDocument) -> str:
    """The label the fact table gives an item ("Menu item: Khachapuri")."""

    return f"{KNOWLEDGE_KIND_LABELS[item.kind]}: {item.title}".strip()


def is_knowledge_fact(fact: BusinessFact, knowledge_labels: set[str]) -> bool:
    """A row built from a knowledge item: its key and its label say so."""

    return str(fact.label) in knowledge_labels and any(
        str(fact.key).startswith(f"{kind.value}_") for kind in KnowledgeItemKind
    )


def build_overview_facts(
    items: Sequence[KnowledgeItemDocument],
    item_count: int,
) -> list[BusinessFact]:
    """How big the catalog is, and the categories of each kind of item."""

    kind_counts: Counter[KnowledgeItemKind] = Counter(item.kind for item in items)
    ordered_kinds: list[KnowledgeItemKind] = [
        kind for kind in KnowledgeItemKind if kind_counts[kind] > 0
    ]
    overview: list[BusinessFact] = [
        BusinessFact(
            key=FactKey("knowledge_base"),
            label=FactLabel("Knowledge base"),
            value=FactValue(
                f"{item_count} items ("
                + ", ".join(
                    f"{kind_counts[kind]} {KNOWLEDGE_KIND_PLURALS[kind]}"
                    for kind in ordered_kinds
                )
                + f"). Only the first {LISTED_KNOWLEDGE_ITEMS} are listed here: "
                "find any other item with search_knowledge and its price with "
                "get_price before you say that something is not offered."
            ),
        )
    ]
    for kind in ordered_kinds:
        categories: list[str] = list_categories(
            [item for item in items if item.kind is kind]
        )
        if categories:
            overview.append(
                BusinessFact(
                    key=FactKey(f"{kind.value}_categories"),
                    label=FactLabel(f"Categories of {KNOWLEDGE_KIND_PLURALS[kind]}"),
                    value=FactValue(", ".join(categories)),
                )
            )

    return overview


def list_categories(items: Sequence[KnowledgeItemDocument]) -> list[str]:
    """
    Tags of the items as words ("gluten_free" -> "gluten free"), the most
    used first (ties by name), at most MAX_CATEGORY_NAMES.
    """

    tag_counts: Counter[str] = Counter(
        str(tag).replace("_", " ").replace("-", " ")
        for item in items
        for tag in item.tags
    )
    ranked: list[tuple[str, int]] = sorted(
        tag_counts.items(),
        key=lambda tag_count: (-tag_count[1], tag_count[0]),
    )
    return [tag for tag, _ in ranked[:MAX_CATEGORY_NAMES]]
