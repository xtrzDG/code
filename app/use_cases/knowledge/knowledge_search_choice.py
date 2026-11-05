"""Which knowledge search the assistant's search_knowledge tool runs."""

from app.contracts.knowledge_embeddings import TextEmbedderContract
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.dto.knowledge import KnowledgeSearchRequest, KnowledgeSearchResult

type KnowledgeSearch = UseCaseContract[KnowledgeSearchRequest, KnowledgeSearchResult]


def choose_knowledge_search(
    text_embedder: TextEmbedderContract,
    hybrid_search: KnowledgeSearch,
    lexical_search: KnowledgeSearch,
) -> KnowledgeSearch:
    """The hybrid search with an embeddings key, the lexical one without."""

    return hybrid_search if text_embedder.is_enabled() else lexical_search
