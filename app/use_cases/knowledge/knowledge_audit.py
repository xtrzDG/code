"""
The audit entry of a change to the knowledge base (AI-11, LOG-06): who
added, changed or deleted which item, in the business's audit log
(`knowledge_item`). The request's address and browser are stamped by the
audit log itself.
"""

from typed_time_provider import Microseconds

from app.contracts.repositories.compliance_repositories import AuditLogRepoContract
from app.schemas.constants.compliance import AuditAction
from app.schemas.domain.compliance import AuditLogEntryDocument
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.compliance.strings import (
    AuditEntityName,
    AuditEntityReference,
)
from app.schemas.typings.knowledge.prefixed_id import KnowledgeItemId
from app.schemas.typings.users.prefixed_id import UserId

KNOWLEDGE_ITEM_ENTITY: AuditEntityName = AuditEntityName("knowledge_item")


def audit_knowledge_change(
    audit_log_repo: AuditLogRepoContract,
    business_id: BusinessId,
    item_id: KnowledgeItemId,
    action: AuditAction,
    actor_id: UserId | None,
    now: Microseconds,
) -> None:
    """Append the entry of one create, update or delete."""

    audit_log_repo.append(
        AuditLogEntryDocument(
            business_id=business_id,
            actor_id=actor_id,
            action=action,
            entity=KNOWLEDGE_ITEM_ENTITY,
            entity_id=AuditEntityReference(str(item_id)),
            created_at=now,
            updated_at=now,
        )
    )
