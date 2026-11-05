from dependency_injector import containers
from dependency_injector.providers import DependenciesContainer, Singleton

from app.containers.adapters.rate_collections_container import (
    RateCollectionsContainer,
)
from app.repositories.exchange_rate_repository import ExchangeRateRepository


class RateRepositoriesContainer(containers.DeclarativeContainer):
    """
    The repository of the dated exchange rates (migration 1071).
    `RepositoriesContainer` extends it: `repositories.exchange_rate_repo`.
    """

    rate_collections: RateCollectionsContainer = DependenciesContainer()  # type: ignore[assignment]

    exchange_rate_repo: Singleton[ExchangeRateRepository] = Singleton(
        ExchangeRateRepository,
        collection=rate_collections.exchange_rate_collection,
    )
