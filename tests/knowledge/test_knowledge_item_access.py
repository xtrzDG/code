"""Listing, isolating and deleting knowledge items."""

from datetime import timedelta

import pytest

from app.schemas.constants.knowledge import KnowledgeItemKind
from app.schemas.dto.knowledge_admin import (
    DeleteKnowledgeItemCommand,
    KnowledgeItemListQuery,
    KnowledgeItemPatch,
    KnowledgeItemQuery,
    UpdateKnowledgeItemCommand,
)
from app.schemas.dto.paging import PageRequest
from app.schemas.exceptions.application_errors import (
    NotFoundError,
)
from app.schemas.typings.platform.constrained_integers import PageSize
from tests.knowledge.harness import KnowledgeHarness
from tests.knowledge.knowledge_base_helpers import add_item, price_titles, search
from tests.knowledge.knowledge_store import DEFAULT_NOW


def test_list_filters_by_kind_and_active_flag_and_pages_newest_first() -> None:
    harness = KnowledgeHarness()
    business = harness.add_business()
    for minute, (title, kind, is_active) in enumerate(
        [
            ("Khinkali", KnowledgeItemKind.MENU_ITEM, True),
            ("adjarian khachapuri", KnowledgeItemKind.MENU_ITEM, True),
            ("Old dish", KnowledgeItemKind.MENU_ITEM, False),
            ("Parking?", KnowledgeItemKind.FAQ, True),
        ]
    ):
        harness.clock_source.set(DEFAULT_NOW + timedelta(minutes=minute))
        add_item(harness, business, title, kind=kind, is_active=is_active)

    everything = harness.list_knowledge_items.run(
        KnowledgeItemListQuery(business_id=business.id)
    )
    active_menu = harness.list_knowledge_items.run(
        KnowledgeItemListQuery(
            business_id=business.id,
            kind=KnowledgeItemKind.MENU_ITEM,
            is_active=True,
        )
    )
    first_page = harness.list_knowledge_items.run(
        KnowledgeItemListQuery(
            business_id=business.id, page=PageRequest(size=PageSize(3))
        )
    )
    assert first_page.next_cursor is not None
    second_page = harness.list_knowledge_items.run(
        KnowledgeItemListQuery(
            business_id=business.id,
            page=PageRequest(size=PageSize(3), cursor=first_page.next_cursor),
        )
    )

    assert [item.title for item in everything.items] == [
        "Parking?",
        "Old dish",
        "adjarian khachapuri",
        "Khinkali",
    ]
    assert everything.next_cursor is None
    assert [item.title for item in active_menu.items] == [
        "adjarian khachapuri",
        "Khinkali",
    ]
    assert [item.title for item in first_page.items] == [
        "Parking?",
        "Old dish",
        "adjarian khachapuri",
    ]
    assert [item.title for item in second_page.items] == ["Khinkali"]
    assert second_page.next_cursor is None


def test_other_businesses_cannot_read_change_or_delete_an_item() -> None:
    harness = KnowledgeHarness()
    owner_business = harness.add_business()
    other_business = harness.add_business()
    created = add_item(harness, owner_business, "Secret recipe", price_minor=100)

    with pytest.raises(NotFoundError):
        harness.get_knowledge_item.run(
            KnowledgeItemQuery(business_id=other_business.id, item_id=created.id)
        )
    with pytest.raises(NotFoundError):
        harness.update_knowledge_item.run(
            UpdateKnowledgeItemCommand(
                business_id=other_business.id,
                item_id=created.id,
                patch=KnowledgeItemPatch(is_active=False),
            )
        )
    with pytest.raises(NotFoundError):
        harness.delete_knowledge_item.run(
            DeleteKnowledgeItemCommand(
                business_id=other_business.id, item_id=created.id
            )
        )

    assert search(harness, other_business, "secret recipe", "en") == []
    assert price_titles(harness, other_business, "secret recipe") == []
    assert (
        harness.get_knowledge_item.run(
            KnowledgeItemQuery(business_id=owner_business.id, item_id=created.id)
        ).title
        == "Secret recipe"
    )


def test_delete_removes_the_item() -> None:
    harness = KnowledgeHarness()
    business = harness.add_business()
    created = add_item(harness, business, "Lobio")

    deletion = harness.delete_knowledge_item.run(
        DeleteKnowledgeItemCommand(business_id=business.id, item_id=created.id)
    )

    assert deletion.id == created.id
    with pytest.raises(NotFoundError):
        harness.delete_knowledge_item.run(
            DeleteKnowledgeItemCommand(business_id=business.id, item_id=created.id)
        )
