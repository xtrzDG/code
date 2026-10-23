from dataclasses import dataclass

from dependency_injector.providers import Factory, Singleton

from app.adapters.embeddings.circuit_text_embedder_adapter import (
    QUERY_EMBEDDINGS_CIRCUIT_POLICY,
)
from app.adapters.embeddings.knowledge_embedding_store_factory import (
    build_knowledge_embedding_store,
)
from app.adapters.embeddings.text_embedder_factory import (
    build_query_text_embedder,
    build_text_embedder,
)
from app.adapters.llm.alias_suggestion.alias_suggestion_adapter import (
    KnowledgeAliasSuggestionAdapter,
)
from app.clients.openai.openai_embeddings_client import (
    QUERY_MAX_RETRIES,
    QUERY_TIMEOUT_SECONDS,
    OpenAiEmbeddingsClient,
)
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
from app.facilitators.resilience.circuit_breaker_facilitator import (
    CircuitBreakerFacilitator,
)
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


@dataclass(frozen=True)
class KnowledgeSearchProviders:
    """
    Knowledge across languages (R17-CROSS-LANG-SEARCH): the embeddings
    endpoint and store, the alias model, the search tool (hybrid with
    EMBEDDINGS_API_KEY, lexical without), aliases on request and the
    `index_knowledge` job. `KnowledgeUseCasesContainer` holds them as its
    own providers, over its own edges.
    """

    text_embedder: Singleton[TextEmbedderContract]
    embedding_store: Singleton[KnowledgeEmbeddingStoreContract]
    alias_suggester: Singleton[KnowledgeAliasSuggesterContract]
    search_knowledge_use_case: Factory[
        UseCaseContract[KnowledgeSearchRequest, KnowledgeSearchResult]
    ]
    suggest_knowledge_aliases_use_case: Factory[
        UseCaseContract[SuggestKnowledgeAliasesCommand, KnowledgeItemDetails]
    ]
    index_knowledge_use_case: Factory[UseCaseContract[QueuedJobInput, JobReport]]


def build_knowledge_search_providers(
    adapters: AdaptersContainer,
    clients: ClientsContainer,
    config: ConfigContainer,
    registries: RegistriesContainer,
    repositories: RepositoriesContainer,
    time_provider: TimeProviderContainer,
    utilities: UtilitiesContainer,
) -> KnowledgeSearchProviders:
    """The providers of the cross-language search over the given edges."""

    text_embedder: Singleton[TextEmbedderContract] = Singleton(
        build_text_embedder,
        settings=config.app_settings,
        client=Singleton(
            OpenAiEmbeddingsClient,
            api_key=config.app_settings.provided.embeddings.api_key,
            base_url=config.app_settings.provided.openai_base_url,
            project_id=config.app_settings.provided.openai_project_id,
        ),
    )
    # Searches embed their query on a short budget behind a breaker; the
    # indexing job above keeps the patient client.
    query_text_embedder: Singleton[TextEmbedderContract] = Singleton(
        build_query_text_embedder,
        settings=config.app_settings,
        client=Singleton(
            OpenAiEmbeddingsClient,
            api_key=config.app_settings.provided.embeddings.api_key,
            base_url=config.app_settings.provided.openai_base_url,
            project_id=config.app_settings.provided.openai_project_id,
            timeout_seconds=QUERY_TIMEOUT_SECONDS,
            max_retries=QUERY_MAX_RETRIES,
        ),
        circuit_breaker=Singleton(
            CircuitBreakerFacilitator,
            monotonic_clock=time_provider.monotonic_clock,
            policy=QUERY_EMBEDDINGS_CIRCUIT_POLICY,
            metrics=utilities.service_metrics,
        ),
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
    knowledge = {
        "business_repo": repositories.business_repo,
        "knowledge_item_repo": repositories.knowledge_item_repo,
    }
    return KnowledgeSearchProviders(
        text_embedder=text_embedder,
        embedding_store=embedding_store,
        alias_suggester=alias_suggester,
        search_knowledge_use_case=Factory(
            choose_knowledge_search,
            text_embedder=text_embedder,
            hybrid_search=Factory(
                EmbeddingSearchKnowledgeUseCase,
                **knowledge,
                brand_knowledge_item_repo=repositories.brand_knowledge_item_repo,
                text_embedder=query_text_embedder,
                embedding_store=embedding_store,
            ),
            lexical_search=Factory(
                SearchKnowledgeUseCase,
                **knowledge,
                brand_knowledge_item_repo=repositories.brand_knowledge_item_repo,
            ),
        ),
        suggest_knowledge_aliases_use_case=Factory(
            SuggestKnowledgeAliasesUseCase,
            **knowledge,
            resource_repo=repositories.resource_repo,
            usage_event_repo=repositories.usage_event_repo,
            alias_suggester=alias_suggester,
            language_detector=utilities.language_detector,
            admit_owner_action=admit_owner_action_factory(registries, time_provider),
            wall_clock=time_provider.microsecond_wall_clock,
        ),
        # The worker's job (INDEX_KNOWLEDGE_JOB).
        index_knowledge_use_case=Factory(
            IndexKnowledgeUseCase,
            **knowledge,
            brand_knowledge_item_repo=repositories.brand_knowledge_item_repo,
            usage_event_repo=repositories.usage_event_repo,
            alias_suggester=alias_suggester,
            language_detector=utilities.language_detector,
            text_embedder=text_embedder,
            embedding_store=embedding_store,
            wall_clock=time_provider.microsecond_wall_clock,
        ),
    )
