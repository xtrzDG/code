"""
Where an item came from survives every edit of its content: the brand's
shared fact it replaces in its location, the assistant answer it corrects
and the import it is a draft of, through a patch and through a re-save of
the whole item (the wizard and the bulk upsert).
"""

from app.schemas.constants.knowledge import KnowledgeItemKind
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.domain.knowledge import KnowledgeItemDocument
from app.schemas.dto.knowledge_admin import (
    KnowledgeItemPatch,
    KnowledgeItemUpsertInput,
    UpdateKnowledgeItemCommand,
    UpsertKnowledgeItemsCommand,
)
from app.schemas.typings.conversations.prefixed_id import MessageId
from app.schemas.typings.knowledge.constrained_strings import KnowledgeShareKey
from app.schemas.typings.knowledge.strings import KnowledgeBody, KnowledgeTitle
from app.schemas.typings.menu_import.prefixed_id import MenuImportBatchId
from tests.knowledge.harness import KnowledgeHarness
from tests.knowledge.knowledge_base_helpers import add_item

SHARED_KEY = KnowledgeShareKey("parking")


def with_lineage(
    harness: KnowledgeHarness, business: BusinessDocument
) -> KnowledgeItemDocument:
    details = add_item(harness, business, "Parking", kind=KnowledgeItemKind.FAQ)
    stored = harness.knowledge_item_repo.get(business.id, details.id)
    assert stored is not None
    marked = stored.model_copy(
        update={
            "shared_key": SHARED_KEY,
            "correction_of": MessageId(),
            "import_batch_id": MenuImportBatchId(),
        }
    )
    harness.knowledge_item_repo.save(marked)
    return marked


def lineage(item: KnowledgeItemDocument | None) -> tuple[object, object, object]:
    assert item is not None
    return item.shared_key, item.correction_of, item.import_batch_id


def test_a_patch_keeps_where_the_item_came_from() -> None:
    harness = KnowledgeHarness()
    business = harness.add_business()
    item = with_lineage(harness, business)

    harness.update_knowledge_item.run(
        UpdateKnowledgeItemCommand(
            business_id=business.id,
            item_id=item.id,
            patch=KnowledgeItemPatch(body=KnowledgeBody("Free behind the house.")),
        )
    )

    assert lineage(harness.knowledge_item_repo.get(business.id, item.id)) == lineage(
        item
    )


def test_a_resave_of_the_whole_item_keeps_where_it_came_from() -> None:
    harness = KnowledgeHarness()
    business = harness.add_business()
    item = with_lineage(harness, business)

    harness.upsert_knowledge_items.run(
        UpsertKnowledgeItemsCommand(
            business_id=business.id,
            items=[
                KnowledgeItemUpsertInput(
                    id=item.id,
                    kind=KnowledgeItemKind.FAQ,
                    title=KnowledgeTitle("Parking"),
                    body=KnowledgeBody("Valet from 18:00."),
                )
            ],
        )
    )

    assert lineage(harness.knowledge_item_repo.get(business.id, item.id)) == lineage(
        item
    )
