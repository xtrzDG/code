"""
A customer's erasure and the knowledge items that name them (PRIV-08): the
items are the owner's own text, so the erasure never changes or deletes
them; it flags each one (`erased_customer_flagged_at`) for the owner, who
sees the flag in the knowledge editor and removes the customer's details
there. Saving the item clears the flag. An item already flagged keeps its
first flag, so the erasure's re-application after a restore changes
nothing.
"""

from typed_time_provider import Microseconds

from app.contracts.repositories.knowledge_repositories import (
    KnowledgeItemRepoContract,
)
from app.schemas.domain.knowledge import KnowledgeItemDocument
from app.schemas.dto.compliance import ContactRecords
from app.schemas.typings.compliance.constrained_integers import (
    FlaggedKnowledgeItemCount,
)
from app.schemas.typings.knowledge.prefixed_id import KnowledgeItemId


def flag_knowledge_mentions(
    knowledge_item_repo: KnowledgeItemRepoContract | None,
    records: ContactRecords,
    now: Microseconds,
) -> FlaggedKnowledgeItemCount:
    """Flag every item that names the customer; how many items are flagged."""

    if knowledge_item_repo is None or not records.knowledge_mentions:
        return FlaggedKnowledgeItemCount(0)

    item_ids: list[KnowledgeItemId] = [
        mention.knowledge_item_id for mention in records.knowledge_mentions
    ]
    items: dict[KnowledgeItemId, KnowledgeItemDocument] = knowledge_item_repo.get_many(
        records.contact.business_id, item_ids
    )
    for item in items.values():
        if item.erased_customer_flagged_at is None:
            knowledge_item_repo.save(
                item.model_copy(update={"erased_customer_flagged_at": now})
            )
    return FlaggedKnowledgeItemCount(len(items))
