from app.contracts.repositories.brand_repositories import (
    BrandKnowledgeItemRepoContract,
)
from app.contracts.repositories.business_repositories import BusinessRepoContract
from app.contracts.repositories.knowledge_repositories import KnowledgeItemRepoContract
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.dto.knowledge import KnowledgeSearchRequest, KnowledgeSearchResult
from app.use_cases.knowledge.knowledge_search_steps import (
    load_searched_knowledge,
    search_result,
)
from app.utilities.knowledge.ranking.lexical_ranking import rank_knowledge_items


class SearchKnowledgeUseCase(
    UseCaseContract[KnowledgeSearchRequest, KnowledgeSearchResult]
):
    """
    Model tool search_knowledge without an embeddings key: up to `limit`
    active facts, best first.

    Ranking is lexical and needs no external model: Unicode folding of case
    and accents, tokens for spaced scripts and character n-grams for
    Chinese, Japanese, Korean and Thai, prefix and typo tolerance, titles
    and their aliases (the title in the business's other languages)
    weighted above tags, attributes and text, rare words above common ones.
    Prices are formatted in the business currency for the request language.

    `EmbeddingSearchKnowledgeUseCase` is the same contract with the meaning
    of the query added (EMBEDDINGS_API_KEY), so callers do not change.
    """

    def __init__(
        self,
        business_repo: BusinessRepoContract,
        knowledge_item_repo: KnowledgeItemRepoContract,
        brand_knowledge_item_repo: BrandKnowledgeItemRepoContract,
    ) -> None:
        self._business_repo: BusinessRepoContract = business_repo
        self._knowledge_item_repo: KnowledgeItemRepoContract = knowledge_item_repo
        self._brand_knowledge_item_repo: BrandKnowledgeItemRepoContract = (
            brand_knowledge_item_repo
        )

    def run(self, input_data: KnowledgeSearchRequest) -> KnowledgeSearchResult:
        business, items = load_searched_knowledge(
            self._business_repo,
            self._knowledge_item_repo,
            self._brand_knowledge_item_repo,
            input_data,
        )
        return search_result(
            business,
            rank_knowledge_items(
                query=input_data.query,
                items=items,
                preferred_languages=[input_data.language],
            ),
            input_data,
        )
