from dependency_injector import containers
from dependency_injector.providers import DependenciesContainer, Singleton

from app.containers.adapters.integration_collections_container import (
    IntegrationCollectionsContainer,
)
from app.repositories.api_key_repository import ApiKeyRepository
from app.repositories.webhook_repositories import (
    WebhookDeliveryRepository,
    WebhookEndpointRepository,
)


class IntegrationRepositoriesContainer(containers.DeclarativeContainer):
    """
    The repositories of the public API and outbound webhooks (migration
    1181). `RepositoriesContainer` extends it, so they are read as
    `repositories.webhook_endpoint_repo` like every other repository.
    """

    integration_collections: IntegrationCollectionsContainer = DependenciesContainer()  # type: ignore[assignment]

    webhook_endpoint_repo: Singleton[WebhookEndpointRepository] = Singleton(
        WebhookEndpointRepository,
        collection=integration_collections.webhook_endpoint_collection,
    )
    webhook_delivery_repo: Singleton[WebhookDeliveryRepository] = Singleton(
        WebhookDeliveryRepository,
        collection=integration_collections.webhook_delivery_collection,
    )
    api_key_repo: Singleton[ApiKeyRepository] = Singleton(
        ApiKeyRepository,
        collection=integration_collections.api_key_collection,
    )
