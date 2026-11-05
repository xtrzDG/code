from dependency_injector.providers import DependenciesContainer, Singleton

from app.containers.adapters.brand_collections_container import (
    BrandCollectionsContainer,
)
from app.containers.integration_repositories import IntegrationRepositoriesContainer
from app.repositories.brand_repositories import (
    BrandKnowledgeItemRepository,
    BrandRepository,
)


class BrandRepositoriesContainer(IntegrationRepositoriesContainer):
    """
    The repositories of brands (migration 1192), on top of the public API's
    and the webhooks' (1181). `RepositoriesContainer` extends it, so they
    are read as `repositories.brand_repo` like every other repository.
    """

    brand_collections: BrandCollectionsContainer = DependenciesContainer()  # type: ignore[assignment]

    brand_repo: Singleton[BrandRepository] = Singleton(
        BrandRepository,
        collection=brand_collections.brand_collection,
    )
    brand_knowledge_item_repo: Singleton[BrandKnowledgeItemRepository] = Singleton(
        BrandKnowledgeItemRepository,
        collection=brand_collections.brand_knowledge_item_collection,
    )
