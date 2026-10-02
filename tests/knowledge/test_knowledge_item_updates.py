"""Changing knowledge items: patches, kept prices and bulk upserts."""

from datetime import UTC, datetime

import pytest

from app.schemas.constants.knowledge import KnowledgeItemKind, KnowledgeItemSource
from app.schemas.dto.knowledge_admin import (
    KnowledgeItemPatch,
    KnowledgeItemUpsertInput,
    UpdateKnowledgeItemCommand,
    UpsertKnowledgeItemsCommand,
)
from app.schemas.exceptions.application_errors import (
    NotFoundError,
    ValidationFailedError,
)
from app.schemas.typings.billing.constrained_integers import MoneyAmountMinor
from app.schemas.typings.knowledge.prefixed_id import KnowledgeItemId
from app.schemas.typings.knowledge.strings import (
    KnowledgeTitle,
)
from app.schemas.typings.localization.constrained_strings import (
    CurrencyCode,
    LanguageTag,
)
from tests.knowledge.harness import KnowledgeHarness
from tests.knowledge.knowledge_base_helpers import add_item


def test_patch_changes_only_given_fields_and_null_clears_optional_ones() -> None:
    harness = KnowledgeHarness()
    business = harness.add_business()
    created = add_item(harness, business, "Lobiani", price_minor=900, body="Beans")
    harness.clock_source.set(datetime(2026, 10, 2, 9, 0, tzinfo=UTC))

    patched = harness.update_knowledge_item.run(
        UpdateKnowledgeItemCommand(
            business_id=business.id,
            item_id=created.id,
            patch=KnowledgeItemPatch.model_validate_json(
                '{"body": null, "price_minor": 1000, "is_active": false}'
            ),
        )
    )

    assert patched.title == "Lobiani"
    assert patched.body is None
    assert patched.price_minor == 1000
    assert patched.currency_code == "GEL"
    assert patched.is_active is False
    assert patched.created_at == created.created_at
    assert patched.updated_at > created.updated_at

    cleared = harness.update_knowledge_item.run(
        UpdateKnowledgeItemCommand(
            business_id=business.id,
            item_id=created.id,
            patch=KnowledgeItemPatch.model_validate_json('{"price_minor": null}'),
        )
    )
    assert cleared.price_minor is None
    assert cleared.currency_code is None
    assert cleared.formatted_price is None

    with pytest.raises(ValidationFailedError, match="title cannot be null"):
        harness.update_knowledge_item.run(
            UpdateKnowledgeItemCommand(
                business_id=business.id,
                item_id=created.id,
                patch=KnowledgeItemPatch.model_validate_json('{"title": null}'),
            )
        )

    with pytest.raises(ValidationFailedError, match="business currency"):
        harness.update_knowledge_item.run(
            UpdateKnowledgeItemCommand(
                business_id=business.id,
                item_id=created.id,
                patch=KnowledgeItemPatch.model_validate_json(
                    '{"currency_code": "USD"}'
                ),
            )
        )


def test_patch_keeps_a_price_set_before_a_currency_change() -> None:
    harness = KnowledgeHarness()
    business = harness.add_business()
    created = add_item(harness, business, "Churchkhela", price_minor=500)
    business.currency_code = CurrencyCode("EUR")
    harness.business_repo.save(business)

    renamed = harness.update_knowledge_item.run(
        UpdateKnowledgeItemCommand(
            business_id=business.id,
            item_id=created.id,
            patch=KnowledgeItemPatch(title=KnowledgeTitle("Churchkhela (walnut)")),
            language=LanguageTag("en"),
        )
    )

    assert renamed.currency_code == "GEL"
    assert renamed.formatted_price == "GEL5.00"


def test_bulk_upsert_matches_by_id_or_title_and_validates_the_whole_batch() -> None:
    harness = KnowledgeHarness()
    business = harness.add_business()
    existing = add_item(harness, business, "Khinkali", price_minor=120)

    saved = harness.upsert_knowledge_items.run(
        UpsertKnowledgeItemsCommand(
            business_id=business.id,
            items=[
                KnowledgeItemUpsertInput(
                    kind=KnowledgeItemKind.MENU_ITEM,
                    title=KnowledgeTitle("KHINKALI"),
                    price_minor=MoneyAmountMinor(150),
                ),
                KnowledgeItemUpsertInput(
                    kind=KnowledgeItemKind.MENU_ITEM,
                    title=KnowledgeTitle("Lobiani"),
                    price_minor=MoneyAmountMinor(900),
                ),
                KnowledgeItemUpsertInput(
                    kind=KnowledgeItemKind.MENU_ITEM,
                    title=KnowledgeTitle("lobiani"),
                    price_minor=MoneyAmountMinor(950),
                ),
            ],
            source=KnowledgeItemSource.MENU_IMPORT,
        )
    )

    assert [item.title for item in saved.items] == ["KHINKALI", "lobiani"]
    assert saved.items[0].id == existing.id
    assert saved.items[0].source is KnowledgeItemSource.OWNER
    assert saved.items[1].source is KnowledgeItemSource.MENU_IMPORT
    assert saved.items[1].price_minor == 950
    assert len(harness.knowledge_item_repo.list_by_business(business.id)) == 2

    with pytest.raises(NotFoundError):
        harness.upsert_knowledge_items.run(
            UpsertKnowledgeItemsCommand(
                business_id=business.id,
                items=[
                    KnowledgeItemUpsertInput(
                        id=KnowledgeItemId(),
                        kind=KnowledgeItemKind.FAQ,
                        title=KnowledgeTitle("Unknown"),
                    )
                ],
            )
        )
