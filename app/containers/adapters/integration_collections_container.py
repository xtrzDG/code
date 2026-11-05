from dependency_injector import containers
from dependency_injector.providers import DependenciesContainer

from app.containers.adapters.document_collection_provider import document_collection
from app.containers.clients import ClientsContainer
from app.containers.config import ConfigContainer
from app.containers.time_provider import TimeProviderContainer
from app.containers.utilities import UtilitiesContainer
from app.schemas.domain.api_keys import ApiKeyDocument
from app.schemas.domain.webhooks import WebhookDeliveryDocument, WebhookEndpointDocument


class IntegrationCollectionsContainer(containers.DeclarativeContainer):
    """
    The document collections of the public API and outbound webhooks
    (migration 1181): webhook endpoints, their deliveries and API keys. A
    sibling of DocumentCollectionsContainer with the same storage factory
    (Postgres with DATABASE_URL, else in memory).
    """

    clients: ClientsContainer = DependenciesContainer()  # type: ignore[assignment]
    config: ConfigContainer = DependenciesContainer()  # type: ignore[assignment]
    time_provider: TimeProviderContainer = DependenciesContainer()  # type: ignore[assignment]
    utilities: UtilitiesContainer = DependenciesContainer()  # type: ignore[assignment]

    webhook_endpoint_collection = document_collection(
        WebhookEndpointDocument,
        "webhook_endpoints",
        config,
        clients,
        utilities,
        time_provider,
    )
    webhook_delivery_collection = document_collection(
        WebhookDeliveryDocument,
        "webhook_deliveries",
        config,
        clients,
        utilities,
        time_provider,
    )
    api_key_collection = document_collection(
        ApiKeyDocument,
        "api_keys",
        config,
        clients,
        utilities,
        time_provider,
    )
