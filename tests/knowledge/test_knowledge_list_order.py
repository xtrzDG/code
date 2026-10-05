"""The knowledge list comes last changed first, a keyset page at a time."""

from datetime import timedelta

from app.schemas.constants.knowledge import KnowledgeItemKind
from app.schemas.dto.knowledge_admin import (
    KnowledgeItemListQuery,
    KnowledgeItemPage,
    KnowledgeItemPatch,
    UpdateKnowledgeItemCommand,
)
from app.schemas.dto.paging import PageRequest
from app.schemas.typings.platform.constrained_integers import PageSize
from tests.knowledge.harness import KnowledgeHarness
from tests.knowledge.knowledge_base_helpers import add_item
from tests.knowledge.knowledge_store import DEFAULT_NOW


def titles(page: KnowledgeItemPage) -> list[str]:
    return [str(item.title) for item in page.items]


def test_an_edited_item_moves_to_the_top_of_the_list() -> None:
    harness = KnowledgeHarness()
    business = harness.add_business()
    created = []
    for minute, title in enumerate(["Khinkali", "Lobio", "Parking?"]):
        harness.clock_source.set(DEFAULT_NOW + timedelta(minutes=minute))
        created.append(add_item(harness, business, title))
    harness.clock_source.set(DEFAULT_NOW + timedelta(minutes=10))
    harness.update_knowledge_item.run(
        UpdateKnowledgeItemCommand(
            business_id=business.id,
            item_id=created[0].id,
            patch=KnowledgeItemPatch(is_active=False),
        )
    )

    everything = harness.list_knowledge_items.run(
        KnowledgeItemListQuery(business_id=business.id)
    )
    inactive = harness.list_knowledge_items.run(
        KnowledgeItemListQuery(business_id=business.id, is_active=False)
    )

    assert titles(everything) == ["Khinkali", "Parking?", "Lobio"]
    assert titles(inactive) == ["Khinkali"]


def test_pages_of_one_kind_follow_each_other_without_gaps() -> None:
    harness = KnowledgeHarness()
    business = harness.add_business()
    for minute in range(7):
        harness.clock_source.set(DEFAULT_NOW + timedelta(minutes=minute))
        add_item(harness, business, f"Dish {minute}")
        add_item(harness, business, f"Question {minute}?", kind=KnowledgeItemKind.FAQ)

    seen: list[str] = []
    cursor = None
    while True:
        page = harness.list_knowledge_items.run(
            KnowledgeItemListQuery(
                business_id=business.id,
                kind=KnowledgeItemKind.FAQ,
                page=PageRequest(size=PageSize(3), cursor=cursor),
            )
        )
        seen.extend(titles(page))
        cursor = page.next_cursor
        if cursor is None:
            break

    assert seen == [f"Question {minute}?" for minute in reversed(range(7))]
