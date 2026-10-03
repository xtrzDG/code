from dependency_injector import containers
from dependency_injector.providers import DependenciesContainer

from app.containers.adapters.document_collection_provider import document_collection
from app.containers.clients import ClientsContainer
from app.containers.config import ConfigContainer
from app.containers.time_provider import TimeProviderContainer
from app.containers.utilities import UtilitiesContainer
from app.schemas.domain.exchange_rates import ExchangeRateDocument


class RateCollectionsContainer(containers.DeclarativeContainer):
    """
    The document collection of the dated exchange rates (migration 1071). A
    sibling of DocumentCollectionsContainer with the same storage factory.
    """

    clients: ClientsContainer = DependenciesContainer()  # type: ignore[assignment]
    config: ConfigContainer = DependenciesContainer()  # type: ignore[assignment]
    time_provider: TimeProviderContainer = DependenciesContainer()  # type: ignore[assignment]
    utilities: UtilitiesContainer = DependenciesContainer()  # type: ignore[assignment]

    exchange_rate_collection = document_collection(
        ExchangeRateDocument,
        "exchange_rates",
        config,
        clients,
        utilities,
        time_provider,
    )
