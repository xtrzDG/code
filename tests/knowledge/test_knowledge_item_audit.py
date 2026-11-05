"""
Every knowledge base change made in the cabinet names its author and is in
the business's audit log (AI-11, LOG-06): who added, changed and deleted
which item.
"""

from datetime import UTC, datetime

from app.schemas.constants.compliance import AuditAction
from app.schemas.constants.knowledge import KnowledgeItemKind
from app.schemas.dto.knowledge_admin import (
    CreateKnowledgeItemCommand,
    DeleteKnowledgeItemCommand,
    KnowledgeItemInput,
    KnowledgeItemPatch,
    UpdateKnowledgeItemCommand,
)
from app.schemas.typings.knowledge.strings import KnowledgeBody, KnowledgeTitle
from app.schemas.typings.users.prefixed_id import UserId
from tests.knowledge.harness import KnowledgeHarness


def test_create_update_and_delete_are_audited_with_their_author() -> None:
    harness = KnowledgeHarness()
    owner, staff = UserId(), UserId()
    business = harness.add_business(owner_id=owner, staff_ids=(staff,))

    created = harness.create_knowledge_item.run(
        CreateKnowledgeItemCommand(
            business_id=business.id,
            item=KnowledgeItemInput(
                kind=KnowledgeItemKind.FAQ,
                title=KnowledgeTitle("Do you take deposits?"),
                body=KnowledgeBody("Groups of six pay 20 GEL a guest."),
            ),
            user_id=owner,
        )
    )
    harness.clock_source.set(datetime(2026, 10, 2, 9, 0, tzinfo=UTC))
    harness.update_knowledge_item.run(
        UpdateKnowledgeItemCommand(
            business_id=business.id,
            item_id=created.id,
            patch=KnowledgeItemPatch.model_validate_json('{"is_active": false}'),
            user_id=staff,
        )
    )
    stored = harness.knowledge_item_repo.get(business.id, created.id)
    assert stored is not None
    assert (stored.created_by, stored.updated_by) == (owner, staff)

    harness.delete_knowledge_item.run(
        DeleteKnowledgeItemCommand(
            business_id=business.id, item_id=created.id, user_id=owner
        )
    )

    entries = [
        entry
        for entry in harness.audit_log_repo.list_by_business(business.id)
        if str(entry.entity) == "knowledge_item"
    ]
    assert [
        (entry.action, entry.actor_id, str(entry.entity_id)) for entry in entries
    ] == [
        (AuditAction.CREATE, owner, str(created.id)),
        (AuditAction.UPDATE, staff, str(created.id)),
        (AuditAction.DELETE, owner, str(created.id)),
    ]


def test_an_item_the_platform_adds_has_no_author() -> None:
    harness = KnowledgeHarness()
    business = harness.add_business()

    created = harness.create_knowledge_item.run(
        CreateKnowledgeItemCommand(
            business_id=business.id,
            item=KnowledgeItemInput(
                kind=KnowledgeItemKind.FAQ, title=KnowledgeTitle("Parking?")
            ),
        )
    )

    stored = harness.knowledge_item_repo.get(business.id, created.id)
    assert stored is not None
    assert stored.created_by is None
    (entry,) = harness.audit_log_repo.list_by_business(business.id)
    assert entry.actor_id is None
    assert entry.action is AuditAction.CREATE
