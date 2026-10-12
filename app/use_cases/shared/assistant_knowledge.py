"""The knowledge an assistant answers from: for assembly and the knowledge tools."""

from app.contracts.repositories.brand_repositories import (
    BrandKnowledgeItemRepoContract,
)
from app.contracts.repositories.knowledge_repositories import (
    KnowledgeItemRepoContract,
)
from app.schemas.domain.brands import BrandKnowledgeItemDocument
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.domain.knowledge import KnowledgeItemDocument
from app.utilities.brands.brand_knowledge_merge import merge_brand_knowledge


def load_active_knowledge(
    knowledge_item_repo: KnowledgeItemRepoContract,
    brand_knowledge_item_repo: BrandKnowledgeItemRepoContract,
    business: BusinessDocument,
) -> list[KnowledgeItemDocument]:
    """
    The business's active items and, for a brand's location, the facts the
    brand shares that the location does not replace (override order in
    `app/utilities/brands/brand_knowledge_merge.py`).
    """

    shared: list[BrandKnowledgeItemDocument] = (
        []
        if business.brand_id is None
        else brand_knowledge_item_repo.list_by_brand(business.brand_id)
    )
    return [
        item
        for item in merge_brand_knowledge(
            knowledge_item_repo.list_by_business(business.id), shared, business
        )
        if item.is_active
    ]
