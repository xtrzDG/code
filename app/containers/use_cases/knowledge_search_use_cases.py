from dependency_injector import containers
from dependency_injector.providers import DependenciesContainer, Factory, Singleton

from app.adapters.embeddings.knowledge_embedding_store_factory import (
    build_knowledge_embedding_store,
)
from app.adapters.embeddings.text_embedder_factory import build_text_embedder
from app.adapters.llm.alias_suggestion.alias_suggestion_adapter import (
    KnowledgeAliasSuggestionAdapter,
)
from app.clients.openai.openai_embeddings_client import OpenAiEmbeddingsClient
from app.containers.adapters.adapters_container import AdaptersContainer
from app.containers.clients import ClientsContainer
from app.containers.config import ConfigContainer
from app.containers.registries import RegistriesContainer
from app.containers.repositories import RepositoriesContainer
from app.containers.time_provider import TimeProviderContainer
from app.containers.use_cases.spend_guard_use_cases import (
    admit_owner_action_factory,
)
from app.containers.utilities import UtilitiesContainer
from app.contracts.knowledge_aliases import KnowledgeAliasSuggesterContract
from app.contracts.knowledge_embeddings import (
    KnowledgeEmbeddingStoreContract,
    TextEmbedderContract,
)
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.dto.jobs import JobReport, QueuedJobInput
from app.schemas.dto.knowledge import KnowledgeSearchRequest, KnowledgeSearchResult
from app.schemas.dto.knowledge_admin import KnowledgeItemDetails
from app.schemas.dto.knowledge_aliases import SuggestKnowledgeAliasesCommand
from app.use_cases.knowledge.aliases.suggest_knowledge_aliases_use_case import (
    SuggestKnowledgeAliasesUseCase,
)
from app.use_cases.knowledge.embedding_search_knowledge_use_case import (
    EmbeddingSearchKnowledgeUseCase,
)
from app.use_cases.knowledge.index_knowledge_use_case import IndexKnowledgeUseCase
from app.use_cases.knowledge.knowledge_search_choice import choose_knowledge_search
from app.use_cases.knowledge.search_knowledge_use_case import SearchKnowledgeUseCase


class KnowledgeSearchUseCasesContainer(containers.DeclarativeContainer):
    """
    Knowledge across languages (R17-CROSS-LANG-SEARCH): the search tool
    (hybrid with EMBEDDINGS_API_KEY, lexical without), aliases suggested by
    the assistants' model, and the `index_knowledge` job that keeps aliases
    and vectors current.
    """

    adapters: AdaptersContainer = DependenciesContainer()  # type: ignore[assignment]
    clients: ClientsContainer = DependenciesContainer()  # type: ignore[assignment]
    config: ConfigContainer = DependenciesContainer()  # type: ignore[assignment]
    registries: RegistriesContainer = DependenciesContainer()  # type: ignore[assignment]
    repositories: RepositoriesContainer = DependenciesContainer()  # type: ignore[assignment]
    time_provider: TimeProviderContainer = DependenciesContainer()  # type: ignore[assignment]
    utilities: UtilitiesContainer = DependenciesContainer()  # type: ignore[assignment]

    # --- The embeddings endpoint (OpenAI EU) and the vectors (pgvector).
    openai_embeddings_client: Singleton[OpenAiEmbeddingsClient] = Singleton(
        OpenAiEmbeddingsClient,
        api_key=config.app_settings.provided.embeddings.api_key,
        base_url=config.app_settings.provided.openai_base_url,
        project_id=config.app_settings.provided.openai_project_id,
    )
    text_embedder: Singleton[TextEmbedderContract] = Singleton(
        build_text_embedder,
        settings=config.app_settings,
        client=openai_embeddings_client,
    )
    embedding_store: Singleton[KnowledgeEmbeddingStoreContract] = Singleton(
        build_knowledge_embedding_store,
        connection_pool=clients.postgres_pool,
        storage_scope=utilities.storage_scope,
        wall_clock=time_provider.microsecond_wall_clock,
    )
    # Aliases are named by the assistants' model (the routed, traced,
    # concurrency-limited adapter), as the website import reads pages.
    alias_suggester: Singleton[KnowledgeAliasSuggesterContract] = Singleton(
        KnowledgeAliasSuggestionAdapter,
        llm_adapter=adapters.llm_adapter,
        model_id=config.app_settings.provided.llm_model_id,
    )

    # --- The model tool search_knowledge and the cabinet's search test.
    lexical_search_use_case: Factory[
        UseCaseContract[KnowledgeSearchRequest, KnowledgeSearchResult]
    ] = Factory(
        SearchKnowledgeUseCase,
        business_repo=repositories.business_repo,
        knowledge_item_repo=repositories.knowledge_item_repo,
        brand_knowledge_item_repo=repositories.brand_knowledge_item_repo,
    )
    hybrid_search_use_case: Factory[
        UseCaseContract[KnowledgeSearchRequest, KnowledgeSearchResult]
    ] = Factory(
        EmbeddingSearchKnowledgeUseCase,
        business_repo=repositories.business_repo,
        knowledge_item_repo=repositories.knowledge_item_repo,
        brand_knowledge_item_repo=repositories.brand_knowledge_item_repo,
        text_embedder=text_embedder,
        embedding_store=embedding_store,
    )
    search_knowledge_use_case: Factory[
        UseCaseContract[KnowledgeSearchRequest, KnowledgeSearchResult]
    ] = Factory(
        choose_knowledge_search,
        text_embedder=text_embedder,
        hybrid_search=hybrid_search_use_case,
        lexical_search=lexical_search_use_case,
    )

    # --- Aliases on request, and the indexing job.
    suggest_knowledge_aliases_use_case: Factory[
        UseCaseContract[SuggestKnowledgeAliasesCommand, KnowledgeItemDetails]
    ] = Factory(
        SuggestKnowledgeAliasesUseCase,
        business_repo=repositories.business_repo,
        knowledge_item_repo=repositories.knowledge_item_repo,
        resource_repo=repositories.resource_repo,
        usage_event_repo=repositories.usage_event_repo,
        alias_suggester=alias_suggester,
        language_detector=utilities.language_detector,
        admit_owner_action=admit_owner_action_factory(registries, time_provider),
        wall_clock=time_provider.microsecond_wall_clock,
    )
    # The worker's job (INDEX_KNOWLEDGE_JOB).
    index_knowledge_use_case: Factory[UseCaseContract[QueuedJobInput, JobReport]] = (
        Factory(
            IndexKnowledgeUseCase,
            business_repo=repositories.business_repo,
            knowledge_item_repo=repositories.knowledge_item_repo,
            brand_knowledge_item_repo=repositories.brand_knowledge_item_repo,
            usage_event_repo=repositories.usage_event_repo,
            alias_suggester=alias_suggester,
            language_detector=utilities.language_detector,
            text_embedder=text_embedder,
            embedding_store=embedding_store,
            wall_clock=time_provider.microsecond_wall_clock,
        )
    )
