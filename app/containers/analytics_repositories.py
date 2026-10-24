from dependency_injector import containers
from dependency_injector.providers import DependenciesContainer, Singleton

from app.containers.adapters.analytics_collections_container import (
    AnalyticsCollectionsContainer,
)
from app.repositories.analytics_repositories import (
    ProductEventRepository,
    WebVitalSampleRepository,
)


class AnalyticsRepositoriesContainer(containers.DeclarativeContainer):
    """
    The repositories of the founder's growth analytics (migration 1074):
    product events and Web Vital samples. `RepositoriesContainer` extends
    it, so they are read as `repositories.product_event_repo`.
    """

    analytics_collections: AnalyticsCollectionsContainer = DependenciesContainer()  # type: ignore[assignment]

    product_event_repo: Singleton[ProductEventRepository] = Singleton(
        ProductEventRepository,
        collection=analytics_collections.product_event_collection,
    )
    web_vital_sample_repo: Singleton[WebVitalSampleRepository] = Singleton(
        WebVitalSampleRepository,
        collection=analytics_collections.web_vital_sample_collection,
    )
