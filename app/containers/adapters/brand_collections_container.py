from dependency_injector import containers
from dependency_injector.providers import DependenciesContainer

from app.containers.adapters.document_collection_provider import document_collection
from app.containers.clients import ClientsContainer
from app.containers.config import ConfigContainer
from app.containers.time_provider import TimeProviderContainer
from app.containers.utilities import UtilitiesContainer
from app.schemas.domain.brands import BrandDocument, BrandKnowledgeItemDocument


class BrandCollectionsContainer(containers.DeclarativeContainer):
    """
    The document collections of brands, chains of locations (migration
    1192): the brands and the knowledge their locations share. A sibling of
    DocumentCollectionsContainer with the same storage factory (Postgres
    with DATABASE_URL, else in memory).
    """

    clients: ClientsContainer = DependenciesContainer()  # type: ignore[assignment]
    config: ConfigContainer = DependenciesContainer()  # type: ignore[assignment]
    time_provider: TimeProviderContainer = DependenciesContainer()  # type: ignore[assignment]
    utilities: UtilitiesContainer = DependenciesContainer()  # type: ignore[assignment]

    brand_collection = document_collection(
        BrandDocument,
        "brands",
        config,
        clients,
        utilities,
        time_provider,
    )
    brand_knowledge_item_collection = document_collection(
        BrandKnowledgeItemDocument,
        "brand_knowledge_items",
        config,
        clients,
        utilities,
        time_provider,
    )
