from app.contracts.repositories.business_repositories import BusinessRepoContract
from app.contracts.repositories.knowledge_repositories import KnowledgeItemRepoContract
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.domain.knowledge import KnowledgeItemDocument
from app.schemas.dto.knowledge import KnowledgeSearchRequest, KnowledgeSearchResult
from app.schemas.exceptions.application_errors import NotFoundError
from app.utilities.knowledge.knowledge_items import to_item_view
from app.utilities.knowledge.lexical_ranking import RankedItem, rank_knowledge_items


class SearchKnowledgeUseCase(
    UseCaseContract[KnowledgeSearchRequest, KnowledgeSearchResult]
):
    """
    Model tool search_knowledge: up to `limit` active facts, best first.

    Ranking is lexical and needs no external model: Unicode folding of case
    and accents, tokens for spaced scripts and character n-grams for
    Chinese, Japanese, Korean and Thai, prefix and typo tolerance, titles
    weighted above tags, attributes and text, rare words above common ones.
    Prices are formatted in the business currency for the request language.

    The concept's embedding search (pgvector) is the next step; it will be
    another implementation of this same contract, so callers do not change.
    """

    def __init__(
        self,
        business_repo: BusinessRepoContract,
        knowledge_item_repo: KnowledgeItemRepoContract,
    ) -> None:
        self._business_repo: BusinessRepoContract = business_repo
        self._knowledge_item_repo: KnowledgeItemRepoContract = knowledge_item_repo

    def run(self, input_data: KnowledgeSearchRequest) -> KnowledgeSearchResult:
        business: BusinessDocument | None = self._business_repo.get(
            input_data.business_id
        )
        if business is None:
            raise NotFoundError(f"Business {input_data.business_id} was not found.")

        active_items: list[KnowledgeItemDocument] = [
            item
            for item in self._knowledge_item_repo.list_by_business(business.id)
            if item.is_active
        ]
        ranked_items: list[RankedItem] = rank_knowledge_items(
            query=input_data.query,
            items=active_items,
            preferred_languages=[input_data.language],
        )
        return KnowledgeSearchResult(
            items=[
                to_item_view(
                    ranked_item.item,
                    business.currency_code,
                    input_data.language,
                )
                for ranked_item in ranked_items[: input_data.limit]
            ]
        )
