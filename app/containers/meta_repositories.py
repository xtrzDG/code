from dependency_injector.providers import DependenciesContainer, Singleton

from app.containers.adapters.meta_collections_container import (
    MetaConnectionCollectionsContainer,
)
from app.containers.brand_repositories import BrandRepositoriesContainer
from app.repositories.meta_connection_state_repository import (
    MetaConnectionStateRepository,
)


class MetaConnectionRepositoriesContainer(BrandRepositoriesContainer):
    """
    The repository of Meta's self-serve connection (migration 1212), on top
    of the brands' (1192). `RepositoriesContainer` extends it, so it is
    read as `repositories.meta_connection_state_repo` like every other one.
    """

    meta_collections: MetaConnectionCollectionsContainer = DependenciesContainer()  # type: ignore[assignment]

    meta_connection_state_repo: Singleton[MetaConnectionStateRepository] = Singleton(
        MetaConnectionStateRepository,
        collection=meta_collections.meta_connection_state_collection,
    )
