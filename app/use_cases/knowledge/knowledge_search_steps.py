"""The steps both knowledge searches share: what they search, what they answer."""

from collections.abc import Sequence

from app.contracts.repositories.brand_repositories import (
    BrandKnowledgeItemRepoContract,
)
from app.contracts.repositories.business_repositories import BusinessRepoContract
from app.contracts.repositories.knowledge_repositories import KnowledgeItemRepoContract
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.domain.knowledge import KnowledgeItemDocument
from app.schemas.dto.knowledge import KnowledgeSearchRequest, KnowledgeSearchResult
from app.use_cases.shared.assistant_knowledge import load_active_knowledge
from app.use_cases.shared.business_access import require_business
from app.utilities.knowledge.knowledge_item_views import to_item_view
from app.utilities.knowledge.ranking.ranked_item import RankedItem


def load_searched_knowledge(
    business_repo: BusinessRepoContract,
    knowledge_item_repo: KnowledgeItemRepoContract,
    brand_knowledge_item_repo: BrandKnowledgeItemRepoContract,
    request: KnowledgeSearchRequest,
) -> tuple[BusinessDocument, list[KnowledgeItemDocument]]:
    """The business (or `NotFoundError`) and the active items it searches."""

    business: BusinessDocument = require_business(business_repo, request.business_id)
    return business, load_active_knowledge(
        knowledge_item_repo, brand_knowledge_item_repo, business
    )


def search_result(
    business: BusinessDocument,
    ranked_items: Sequence[RankedItem],
    request: KnowledgeSearchRequest,
) -> KnowledgeSearchResult:
    """Up to `limit` items, best first, priced in the request's language."""

    return KnowledgeSearchResult(
        items=[
            to_item_view(ranked_item.item, business.currency_code, request.language)
            for ranked_item in ranked_items[: int(request.limit)]
        ]
    )
