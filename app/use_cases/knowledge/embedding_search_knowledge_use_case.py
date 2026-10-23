import logging

from app.contracts.knowledge_embeddings import (
    EmbeddingVector,
    KnowledgeEmbeddingStoreContract,
    TextEmbedderContract,
)
from app.contracts.repositories.brand_repositories import (
    BrandKnowledgeItemRepoContract,
)
from app.contracts.repositories.business_repositories import BusinessRepoContract
from app.contracts.repositories.knowledge_repositories import KnowledgeItemRepoContract
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.dto.knowledge import KnowledgeSearchRequest, KnowledgeSearchResult
from app.schemas.dto.knowledge_embeddings import KnowledgeNeighbour
from app.schemas.exceptions.application_errors import ExternalServiceError
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.knowledge.constrained_integers import EmbeddingNeighbourLimit
from app.schemas.typings.knowledge.strings import EmbeddingInputText
from app.use_cases.knowledge.knowledge_search_steps import (
    load_searched_knowledge,
    search_result,
)
from app.utilities.knowledge.embeddings.embedding_texts import current_neighbours
from app.utilities.knowledge.ranking.hybrid_ranking import rank_hybrid
from app.utilities.knowledge.ranking.lexical_ranking import rank_knowledge_items
from app.utilities.knowledge.ranking.ranked_item import RankedItem

LOGGER: logging.Logger = logging.getLogger(__name__)
# The nearest items read for a search: enough to rescue the few the words
# miss, few enough to rank in a millisecond.
NEIGHBOURS_PER_SEARCH: int = 30


class EmbeddingSearchKnowledgeUseCase(
    UseCaseContract[KnowledgeSearchRequest, KnowledgeSearchResult]
):
    """
    Model tool search_knowledge with an embeddings key: the lexical ranking
    of `SearchKnowledgeUseCase` joined with the meaning of the query, the
    cosine similarity of its embedding (an EU endpoint) to the items'
    vectors in pgvector (`hybrid_ranking`). A question in Georgian finds an
    item titled in English even before the owner gave it a Georgian alias.

    The query is embedded once per search, on a short budget behind a
    circuit breaker (`build_query_text_embedder`). When the endpoint fails
    or is slow, or the database has no pgvector, the search is the lexical
    one; a missing or stale vector (an item edited since its last
    indexing: its fingerprint no longer matches) leaves that item to its
    words until the `index_knowledge` job the edit queued has run.
    """

    def __init__(
        self,
        business_repo: BusinessRepoContract,
        knowledge_item_repo: KnowledgeItemRepoContract,
        brand_knowledge_item_repo: BrandKnowledgeItemRepoContract,
        text_embedder: TextEmbedderContract,
        embedding_store: KnowledgeEmbeddingStoreContract,
    ) -> None:
        self._business_repo: BusinessRepoContract = business_repo
        self._knowledge_item_repo: KnowledgeItemRepoContract = knowledge_item_repo
        self._brand_knowledge_item_repo: BrandKnowledgeItemRepoContract = (
            brand_knowledge_item_repo
        )
        self._text_embedder: TextEmbedderContract = text_embedder
        self._embedding_store: KnowledgeEmbeddingStoreContract = embedding_store

    def run(self, input_data: KnowledgeSearchRequest) -> KnowledgeSearchResult:
        business, items = load_searched_knowledge(
            self._business_repo,
            self._knowledge_item_repo,
            self._brand_knowledge_item_repo,
            input_data,
        )
        lexical: list[RankedItem] = rank_knowledge_items(
            query=input_data.query,
            items=items,
            preferred_languages=[input_data.language],
        )
        neighbours: list[KnowledgeNeighbour] = current_neighbours(
            self._nearest(business.id, input_data) if items else [],
            items,
            self._text_embedder.model_id(),
        )
        return search_result(
            business,
            rank_hybrid(lexical, neighbours, items) if neighbours else lexical,
            input_data,
        )

    def _nearest(
        self, business_id: BusinessId, request: KnowledgeSearchRequest
    ) -> list[KnowledgeNeighbour]:
        """The items closest in meaning; none when embeddings are unavailable."""

        if not self._text_embedder.is_enabled():
            return []

        try:
            if not self._embedding_store.is_available():
                return []

            vectors: list[EmbeddingVector] = self._text_embedder.embed(
                [EmbeddingInputText(str(request.query))]
            )
            return self._embedding_store.nearest(
                business_id,
                self._text_embedder.model_id(),
                vectors[0],
                EmbeddingNeighbourLimit(NEIGHBOURS_PER_SEARCH),
            )
        except ExternalServiceError as error:
            # The query is a customer's words: never logged.
            LOGGER.warning(
                "Knowledge embeddings unavailable (%s); the search is lexical.",
                type(error).__name__,
            )
            return []
